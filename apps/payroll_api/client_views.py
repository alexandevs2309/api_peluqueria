"""
Vistas simplificadas de payroll para /client
SOLO funcionalidades básicas, SIN complejidad avanzada
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction, models
from django.utils import timezone
from datetime import datetime, timedelta
from .models import PayrollSettlement
from .services import PayrollSettlementService
from apps.employees_api.payroll_models import PayrollPayment
from apps.employees_api.models import Employee

class ClientPayrollViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """GET /api/client/payroll/periods/ - Lista períodos simples"""
        # Solo empleados activos con configuración simple
        employees = Employee.objects.filter(
            tenant=self.request.user.tenant,
            is_active=True,
            commission_payment_mode='PER_PERIOD'  # BLOQUEAR ON_DEMAND
        ).exclude(salary_type='mixed')  # BLOQUEAR mixto
        
        # Generar períodos automáticamente
        self._ensure_current_periods(self.request.user.tenant)
        
        # Calcular período actual
        today = timezone.now().date()
        current_year = today.year
        
        if today.day <= 15:
            period_index = (today.month - 1) * 2 + 1
        else:
            period_index = (today.month - 1) * 2 + 2
        
        # Obtener SOLO settlements del período actual
        settlements = PayrollSettlement.objects.filter(
            tenant=self.request.user.tenant,
            employee__in=employees,
            period_year=current_year,
            period_index=period_index
            # MOSTRAR TODOS LOS ESTADOS: OPEN, READY, PAID
        ).select_related('employee__user').order_by(
            # Orden lógico: OPEN → READY → PAID
            models.Case(
                models.When(status='OPEN', then=models.Value(1)),
                models.When(status='READY', then=models.Value(2)),
                models.When(status='PAID', then=models.Value(3)),
                default=models.Value(4),
                output_field=models.IntegerField()
            ),
            'employee__user__email'
        )
        
        results = []
        for settlement in settlements:
            results.append({
                'id': settlement.id,
                'employee_name': settlement.employee.user.full_name or settlement.employee.user.email,
                'period_display': self._format_period(settlement),
                'status': settlement.status.lower(),
                'gross_amount': float(settlement.gross_amount),
                'total_salary_amount': float(settlement.gross_amount),  # Nuevo naming: salario total bruto
                'net_amount': float(settlement.net_amount),
                'deductions_total': float(settlement.total_deductions),
                'period_start': settlement.period_start,
                'period_end': settlement.period_end,
                'can_pay': settlement.can_pay,
                'pay_block_reason': settlement.pay_block_reason
            })
        
        return Response({'periods': results})
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """GET /api/client/payroll/periods/history/ - Historial de pagos"""
        # Solo empleados activos
        employees = Employee.objects.filter(
            tenant=self.request.user.tenant,
            is_active=True
        )
        
        # Obtener solo settlements pagados
        settlements = PayrollSettlement.objects.filter(
            tenant=self.request.user.tenant,
            employee__in=employees,
            status='PAID'  # SOLO pagados para historial
        ).select_related('employee__user').order_by('-closed_at')
        
        results = []
        for settlement in settlements:
            results.append({
                'id': settlement.id,
                'employee_name': settlement.employee.user.full_name or settlement.employee.user.email,
                'period_display': self._format_period(settlement),
                'status': settlement.status.lower(),
                'gross_amount': float(settlement.gross_amount),
                'total_salary_amount': float(settlement.gross_amount),  # Nuevo naming: salario total bruto
                'net_amount': float(settlement.net_amount),
                'deductions_total': float(settlement.total_deductions),
                'period_start': settlement.period_start,
                'period_end': settlement.period_end,
                'paid_at': settlement.closed_at,
                'paid_by': settlement.closed_by.full_name if settlement.closed_by else 'Sistema'
            })
        
        return Response({'history': results})
    
    @action(detail=True, methods=['post'])
    def close_period(self, request, pk=None):
        """POST /api/client/payroll/periods/{id}/close/ - Calcular período"""
        try:
            settlement = PayrollSettlement.objects.get(
                id=pk,
                tenant=request.user.tenant,
                status='OPEN'  # SOLO períodos abiertos
            )
            
            # VALIDAR configuración simple
            if settlement.employee.commission_payment_mode == 'ON_DEMAND':
                return Response({'error': 'Empleado configurado para retiros libres'}, status=400)
            
            if settlement.employee.salary_type == 'mixed':
                return Response({'error': 'Empleado con configuración mixta no soportada'}, status=400)
            
            # Calcular usando servicio existente
            service = PayrollSettlementService()
            settlement = service.calculate_settlement(settlement)
            
            # Marcar como listo si tiene montos
            if settlement.gross_amount > 0:
                settlement.status = 'READY'
                settlement.closed_at = timezone.now()
                settlement.closed_by = request.user
                settlement.save()
            
            return Response({
                'id': settlement.id,
                'status': settlement.status.lower(),
                'gross_amount': float(settlement.gross_amount),
                'net_amount': float(settlement.net_amount),
                'deductions_total': float(settlement.total_deductions)
            })
            
        except PayrollSettlement.DoesNotExist:
            return Response({'error': 'Período no encontrado'}, status=404)
    
    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """POST /api/client/payroll/periods/{id}/recalculate/ - Recálculo forzado"""
        try:
            settlement = PayrollSettlement.objects.get(
                id=pk,
                tenant=request.user.tenant
            )
            
            # No permitir recálculo de períodos ya pagados
            if settlement.status == 'PAID':
                return Response({'error': 'No se puede recalcular un período ya pagado'}, status=400)
            
            # Guardar valores anteriores para auditoría
            old_values = {
                'fixed_salary': float(settlement.fixed_salary_amount),
                'commission': float(settlement.commission_amount),
                'gross': float(settlement.gross_amount),
                'net': float(settlement.net_amount)
            }
            
            # Recalcular usando servicio
            service = PayrollSettlementService()
            settlement = service.calculate_settlement(settlement)
            
            # Actualizar estado según resultado
            if settlement.gross_amount > 0:
                settlement.status = 'READY'
                settlement.closed_at = timezone.now()
                settlement.closed_by = request.user
            else:
                settlement.status = 'OPEN'
                settlement.closed_at = None
                settlement.closed_by = None
            
            settlement.save()
            
            return Response({
                'message': 'Período recalculado exitosamente',
                'settlement_id': settlement.id,
                'status': settlement.status.lower(),
                'previous_values': old_values,
                'current_values': {
                    'fixed_salary': float(settlement.fixed_salary_amount),
                    'commission': float(settlement.commission_amount),
                    'gross': float(settlement.gross_amount),
                    'net': float(settlement.net_amount)
                },
                'recalculated_by': request.user.full_name or request.user.email,
                'recalculated_at': timezone.now().isoformat()
            })
            
        except PayrollSettlement.DoesNotExist:
            return Response({'error': 'Período no encontrado'}, status=404)
    
    @action(detail=False, methods=['post'])
    def register_payment(self, request):
        """POST /api/client/payroll/payments/ - Registrar pago simple"""
        period_id = request.data.get('period_id')
        payment_method = request.data.get('payment_method', 'cash')
        payment_reference = request.data.get('payment_reference', '')
        
        if not period_id:
            return Response({'error': 'period_id requerido'}, status=400)
        
        try:
            with transaction.atomic():
                settlement = PayrollSettlement.objects.get(
                    id=period_id,
                    tenant=request.user.tenant,
                    status='READY'  # SOLO períodos listos
                )
                
                # VALIDAR ciclo de pago
                if not settlement.can_pay:
                    return Response({
                        'error': 'No se puede pagar en este momento',
                        'reason': settlement.pay_block_reason
                    }, status=400)
                
                # Crear pago simple
                payment = PayrollPayment.objects.create(
                    employee=settlement.employee,
                    tenant=settlement.tenant,
                    payment_type='PAYROLL',  # SOLO tipo payroll
                    gross_amount=settlement.gross_amount,
                    net_amount=settlement.net_amount,
                    total_deductions=settlement.total_deductions,
                    payment_method=payment_method,
                    payment_reference=payment_reference,
                    period_start_date=settlement.period_start,
                    period_end_date=settlement.period_end,
                    period_year=settlement.period_year,
                    period_index=settlement.period_index,
                    period_frequency='biweekly',
                    paid_by=request.user,
                    status='COMPLETED'  # SOLO estado completado
                )
                
                # Marcar settlement como pagado
                service = PayrollSettlementService()
                service.mark_as_paid(settlement)
                
                return Response({
                    'payment_id': str(payment.payment_id),
                    'message': 'Pago registrado exitosamente',
                    'amount_paid': float(payment.net_amount),
                    'paid_at': payment.paid_at.isoformat()
                })
                
        except PayrollSettlement.DoesNotExist:
            return Response({'error': 'Período no encontrado o no está listo'}, status=404)
    
    @action(detail=False, methods=['get'], url_path='payments/(?P<payment_id>[^/.]+)/receipt')
    def payment_receipt(self, request, payment_id=None):
        """GET /api/client/payroll/payments/{id}/receipt/ - Recibo de pago"""
        try:
            payment = PayrollPayment.objects.select_related(
                'employee__user', 'tenant', 'paid_by'
            ).get(
                payment_id=payment_id,
                tenant=request.user.tenant
            )
            
            # Formatear período
            month_names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                          'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
            month = ((payment.period_index - 1) // 2) + 1
            half = "1ra" if (payment.period_index % 2) == 1 else "2da"
            period_display = f"{half} quincena {month_names[month-1]} {payment.period_year}"
            
            receipt_data = {
                'payment_id': str(payment.payment_id),
                'employee': {
                    'name': payment.employee.user.full_name or payment.employee.user.email,
                    'email': payment.employee.user.email
                },
                'period': {
                    'display': period_display,
                    'start_date': payment.period_start_date,
                    'end_date': payment.period_end_date,
                    'frequency': payment.period_frequency
                },
                'amounts': {
                    'gross_amount': float(payment.gross_amount),
                    'deductions': {
                        'afp': float(payment.afp_deduction),
                        'sfs': float(payment.sfs_deduction),
                        'isr': float(payment.isr_deduction),
                        'loans': float(payment.loan_deductions),
                        'total': float(payment.total_deductions)
                    },
                    'net_amount': float(payment.net_amount)
                },
                'payment_info': {
                    'method': payment.payment_method,
                    'reference': payment.payment_reference or 'N/A',
                    'paid_at': payment.paid_at.isoformat(),
                    'paid_by': payment.paid_by.full_name if payment.paid_by else 'Sistema'
                },
                'company': {
                    'name': 'Barbería App',
                    'address': 'Dirección de la empresa',
                    'phone': 'Teléfono de contacto'
                }
            }
            
            return Response(receipt_data)
            
        except PayrollPayment.DoesNotExist:
            return Response({'error': 'Pago no encontrado'}, status=404)
    
    def _ensure_current_periods(self, tenant):
        """Generar períodos automáticamente - SOLO quincenales"""
        today = timezone.now().date()
        current_year = today.year
        
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
            period_end = (next_month - timedelta(days=1))
            period_index = (today.month - 1) * 2 + 2
        
        # Solo empleados con configuración simple
        employees = Employee.objects.filter(
            tenant=tenant,
            is_active=True,
            commission_payment_mode='PER_PERIOD'
        ).exclude(salary_type='mixed')
        
        service = PayrollSettlementService()
        
        for employee in employees:
            # Obtener o crear settlement para el período actual
            settlement, created = PayrollSettlement.objects.get_or_create(
                employee=employee,
                period_year=current_year,
                period_index=period_index,
                frequency='biweekly',
                defaults={
                    'tenant': tenant,
                    'period_start': period_start,
                    'period_end': period_end,
                    'status': 'OPEN'
                }
            )
            
            # Calcular automáticamente si se creó o si está en OPEN
            if created or settlement.status == 'OPEN':
                settlement = service.calculate_settlement(settlement)
                # Marcar como READY si tiene cualquier monto (salario fijo o comisión)
                if settlement.gross_amount > 0:
                    settlement.status = 'READY'
                    settlement.save()
                # Para empleados fixed sin earnings, mantener OPEN para que aparezcan
                elif settlement.status == 'OPEN':
                    settlement.save()
    
    def _format_period(self, settlement):
        """Formatear período para display"""
        month_names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                      'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        month = ((settlement.period_index - 1) // 2) + 1
        half = "1ra" if (settlement.period_index % 2) == 1 else "2da"
        return f"{half} quincena {month_names[month-1]} {settlement.period_year}"