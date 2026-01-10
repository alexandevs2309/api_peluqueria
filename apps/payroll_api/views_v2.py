"""
Adaptador de APIs - Mantiene compatibilidad con frontend
Usa nueva arquitectura internamente
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from .models import PayrollSettlement, PayrollPeriod, PayrollCalculation, PayrollPaymentNew
from .calculation_engine import PayrollService, PayrollCalculationEngine
from apps.employees_api.models import Employee
import structlog

logger = structlog.get_logger("apps.payroll_api")

class PayrollSettlementViewSetV2(viewsets.ModelViewSet):
    """
    API adaptada que usa nueva arquitectura internamente
    Mantiene compatibilidad con contratos existentes
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PayrollCalculation.objects.filter(
            tenant=self.request.user.tenant,
            is_current=True
        ).select_related('employee__user', 'period')
    
    def list(self, request):
        """Listar cálculos actuales (compatible con settlements)"""
        logger.info("payroll_list_requested", 
                   user_id=request.user.id,
                   tenant_id=request.user.tenant_id)
        
        # Asegurar períodos actuales
        self._ensure_current_periods(request.user.tenant)
        
        calculations = self.get_queryset().filter(
            period__status__in=['OPEN', 'CLOSED']
        )
        
        results = []
        for calc in calculations:
            # Mapear a formato legacy para compatibilidad
            results.append({
                'id': calc.id,
                'settlement_id': str(calc.calculation_id),  # Usar calculation_id como settlement_id
                'employee': calc.employee.id,
                'employee_name': calc.employee.user.full_name or calc.employee.user.email,
                'frequency': calc.period.frequency,
                'period_start': calc.period.period_start,
                'period_end': calc.period.period_end,
                'period_year': calc.period.period_year,
                'period_index': calc.period.period_index,
                'status': self._map_status(calc.period.status, calc),
                'fixed_salary_amount': float(calc.base_salary),
                'commission_amount': float(calc.commission_total),
                'commission_salary_amount': float(calc.commission_total),
                'gross_amount': float(calc.gross_total),
                'total_salary_amount': float(calc.gross_total),
                'net_amount': float(calc.net_amount),
                'created_at': calc.calculated_at,
                'closed_at': calc.period.closed_at,
                # Nuevos campos para debugging
                '_version': calc.version,
                '_breakdown_available': bool(calc.calculation_breakdown)
            })
        
        logger.info("payroll_list_completed", 
                   calculations_count=len(results),
                   tenant_id=request.user.tenant_id)
        
        return Response({
            'results': results,
            'count': len(results)
        })
    
    @action(detail=True, methods=['get'])
    def breakdown(self, request, pk=None):
        """Nuevo endpoint: obtener breakdown detallado"""
        try:
            calculation = PayrollCalculation.objects.get(
                id=pk,
                tenant=request.user.tenant
            )
            
            logger.info("payroll_breakdown_requested",
                       calculation_id=str(calculation.calculation_id),
                       employee_id=calculation.employee.id)
            
            return Response({
                'calculation_id': str(calculation.calculation_id),
                'version': calculation.version,
                'breakdown': calculation.calculation_breakdown,
                'calculated_at': calculation.calculated_at,
                'calculated_by': calculation.calculated_by.email if calculation.calculated_by else None
            })
            
        except PayrollCalculation.DoesNotExist:
            return Response({'error': 'Calculation not found'}, status=404)
    
    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """Nuevo endpoint: recalcular nómina (crea nueva versión)"""
        try:
            old_calculation = PayrollCalculation.objects.get(
                id=pk,
                tenant=request.user.tenant
            )
            
            logger.info("payroll_recalculation_requested",
                       calculation_id=str(old_calculation.calculation_id),
                       current_version=old_calculation.version,
                       requested_by=request.user.id)
            
            # Crear nueva versión
            new_calculation = PayrollService.calculate_payroll(
                employee=old_calculation.employee,
                period=old_calculation.period,
                calculated_by=request.user
            )
            
            logger.info("payroll_recalculation_completed",
                       old_calculation_id=str(old_calculation.calculation_id),
                       new_calculation_id=str(new_calculation.calculation_id),
                       new_version=new_calculation.version)
            
            return Response({
                'status': 'success',
                'message': 'Recalculation completed',
                'old_version': old_calculation.version,
                'new_version': new_calculation.version,
                'calculation_id': str(new_calculation.calculation_id),
                'changes': self._compare_calculations(old_calculation, new_calculation)
            })
            
        except PayrollCalculation.DoesNotExist:
            return Response({'error': 'Calculation not found'}, status=404)
        except Exception as e:
            logger.error("payroll_recalculation_failed",
                        calculation_id=pk,
                        error=str(e),
                        exc_info=True)
            return Response({'error': 'Recalculation failed'}, status=500)
    
    def _ensure_current_periods(self, tenant):
        """Crear períodos actuales si no existen"""
        today = timezone.now().date()
        current_year = today.year
        
        # Calcular período quincenal actual
        if today.day <= 15:
            period_start = today.replace(day=1)
            period_end = today.replace(day=15)
            period_index = (today.month - 1) * 2 + 1
        else:
            period_start = today.replace(day=16)
            if today.month == 12:
                next_month = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_month = today.replace(month=today.month + 1, day=1)
            period_end = (next_month - timezone.timedelta(days=1))
            period_index = (today.month - 1) * 2 + 2
        
        # Crear período si no existe
        period, created = PayrollPeriod.objects.get_or_create(
            tenant=tenant,
            frequency='biweekly',
            period_year=current_year,
            period_index=period_index,
            defaults={
                'period_start': period_start,
                'period_end': period_end,
                'status': 'OPEN'
            }
        )
        
        if created:
            logger.info("period_auto_created",
                       period_id=str(period.period_id),
                       tenant_id=tenant.id)
            
            # Crear cálculos para empleados activos
            employees = Employee.objects.filter(tenant=tenant, is_active=True)
            for employee in employees:
                try:
                    PayrollService.calculate_payroll(
                        employee=employee,
                        period=period
                    )
                except Exception as e:
                    logger.error("auto_calculation_failed",
                               employee_id=employee.id,
                               period_id=str(period.period_id),
                               error=str(e))
    
    def _map_status(self, period_status, calculation):
        """Mapear status de período a status legacy"""
        if hasattr(calculation, 'payment_new'):
            return 'PAID'
        elif period_status == 'CLOSED':
            return 'READY'
        else:
            return 'OPEN'
    
    def _compare_calculations(self, old_calc, new_calc):
        """Comparar dos cálculos para mostrar cambios"""
        changes = {}
        
        fields_to_compare = [
            'base_salary', 'commission_total', 'gross_total',
            'legal_deductions', 'loan_deductions', 'total_deductions', 'net_amount'
        ]
        
        for field in fields_to_compare:
            old_value = getattr(old_calc, field)
            new_value = getattr(new_calc, field)
            if old_value != new_value:
                changes[field] = {
                    'old': str(old_value),
                    'new': str(new_value),
                    'difference': str(new_value - old_value)
                }
        
        return changes

class PayrollPaymentViewSetV2(viewsets.ViewSet):
    """
    API de pagos adaptada para nueva arquitectura
    """
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Listar historial de pagos"""
        payments = PayrollPaymentNew.objects.filter(
            tenant=request.user.tenant
        ).select_related('calculation__employee__user').order_by('-paid_at')
        
        results = []
        for payment in payments:
            calc = payment.calculation
            results.append({
                'id': payment.id,
                'payment_id': str(payment.payment_id),
                'employee_id': calc.employee.id,
                'employee_name': calc.employee.user.full_name or calc.employee.user.email,
                'payment_type': 'PAYROLL',
                'gross_amount': float(calc.gross_total),
                'total_salary_amount': float(calc.gross_total),
                'net_amount': float(payment.amount_paid),
                'payment_method': payment.payment_method,
                'payment_reference': payment.payment_reference,
                'payment_notes': payment.payment_notes,
                'period_start': calc.period.period_start,
                'period_end': calc.period.period_end,
                'paid_at': payment.paid_at,
                'status': 'COMPLETED',
                # Nuevos campos
                'calculation_version': calc.version,
                'breakdown_available': bool(calc.calculation_breakdown)
            })
        
        return Response({
            'results': results,
            'count': len(results)
        })
    
    @action(detail=False, methods=['post'])
    def execute_payment(self, request):
        """Ejecutar pago usando nueva arquitectura"""
        calculation_id = request.data.get('settlement_id')  # Mantener nombre legacy
        payment_method = request.data.get('payment_method', 'cash')
        payment_reference = request.data.get('payment_reference', '')
        payment_notes = request.data.get('payment_notes', '')
        
        if not calculation_id:
            return Response({'error': 'settlement_id es requerido'}, status=400)
        
        try:
            with transaction.atomic():
                # Obtener calculation por ID o calculation_id
                try:
                    calculation = PayrollCalculation.objects.get(
                        id=calculation_id,
                        tenant=request.user.tenant,
                        is_current=True
                    )
                except PayrollCalculation.DoesNotExist:
                    calculation = PayrollCalculation.objects.get(
                        calculation_id=calculation_id,
                        tenant=request.user.tenant,
                        is_current=True
                    )
                
                # Verificar que no esté ya pagado
                if hasattr(calculation, 'payment_new'):
                    return Response({
                        'error': 'Payment already executed',
                        'existing_payment_id': calculation.payment_new.id
                    }, status=400)
                
                # Ejecutar pago
                payment = PayrollService.execute_payment(
                    calculation=calculation,
                    paid_by=request.user,
                    payment_method=payment_method,
                    payment_reference=payment_reference,
                    payment_notes=payment_notes
                )
                
                logger.info("payroll_payment_executed",
                           payment_id=str(payment.payment_id),
                           calculation_id=str(calculation.calculation_id),
                           employee_id=calculation.employee.id,
                           amount=str(payment.amount_paid),
                           paid_by=request.user.id)
                
                return Response({
                    'status': 'success',
                    'message': 'Pago ejecutado correctamente',
                    'payment_id': payment.id,
                    'settlement_id': calculation.id,  # Mantener compatibilidad
                    'amount_paid': float(payment.amount_paid),
                    'paid_at': payment.paid_at.isoformat(),
                    'calculation_version': calculation.version
                })
                
        except PayrollCalculation.DoesNotExist:
            return Response({'error': 'Calculation not found'}, status=404)
        except Exception as e:
            logger.error("payroll_payment_failed",
                        calculation_id=calculation_id,
                        error=str(e),
                        exc_info=True)
            return Response({'error': f'Payment failed: {str(e)}'}, status=500)