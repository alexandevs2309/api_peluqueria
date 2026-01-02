from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from .models import PayrollSettlement, SettlementEarning
from .services import PayrollSettlementService
from apps.employees_api.payroll_models import PayrollPayment
from apps.employees_api.models import Employee

class PayrollSettlementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PayrollSettlement.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('employee__user')
    
    def list(self, request):
        """Listar liquidaciones del tenant"""
        # Generar liquidaciones automáticamente si no existen
        self._ensure_current_settlements(request.user.tenant)
        
        settlements = self.get_queryset().filter(status__in=['OPEN', 'READY'])
        
        results = []
        for settlement in settlements:
            results.append({
                'id': settlement.id,
                'settlement_id': str(settlement.settlement_id),
                'employee': settlement.employee.id,
                'employee_name': settlement.employee.user.full_name or settlement.employee.user.email,
                'frequency': settlement.frequency,
                'period_start': settlement.period_start,
                'period_end': settlement.period_end,
                'period_year': settlement.period_year,
                'period_index': settlement.period_index,
                'status': settlement.status,
                'fixed_salary_amount': float(settlement.fixed_salary_amount),
                'commission_amount': float(settlement.commission_amount),
                'gross_amount': float(settlement.gross_amount),
                'net_amount': float(settlement.net_amount),
                'created_at': settlement.created_at,
                'closed_at': settlement.closed_at
            })
        
        return Response({
            'results': results,
            'count': len(results)
        })
    
    def _ensure_current_settlements(self, tenant):
        """Crear liquidaciones para el período actual si no existen"""
        today = timezone.now().date()
        current_year = today.year
        
        # Calcular período quincenal actual
        if today.day <= 15:
            period_start = today.replace(day=1)
            period_end = today.replace(day=15)
            period_index = (today.month - 1) * 2 + 1
        else:
            period_start = today.replace(day=16)
            # Último día del mes
            if today.month == 12:
                next_month = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_month = today.replace(month=today.month + 1, day=1)
            period_end = (next_month - timedelta(days=1))
            period_index = (today.month - 1) * 2 + 2
        
        # Obtener empleados activos
        employees = Employee.objects.filter(
            tenant=tenant,
            is_active=True
        )
        
        service = PayrollSettlementService()
        
        for employee in employees:
            # Verificar si ya existe liquidación para este período
            existing = PayrollSettlement.objects.filter(
                employee=employee,
                period_year=current_year,
                period_index=period_index,
                frequency='biweekly'
            ).first()
            
            if not existing:
                # Crear nueva liquidación
                settlement = PayrollSettlement.objects.create(
                    employee=employee,
                    tenant=tenant,
                    frequency='biweekly',
                    period_start=period_start,
                    period_end=period_end,
                    period_year=current_year,
                    period_index=period_index,
                    status='OPEN'
                )
                
                # Calcular montos
                service.calculate_settlement(settlement)
                
                # Marcar como listo si tiene montos
                if settlement.gross_amount > 0:
                    settlement.status = 'READY'
                    settlement.save()

class PayrollPaymentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Listar historial de pagos"""
        payments = PayrollPayment.objects.filter(
            tenant=request.user.tenant
        ).select_related('employee__user').order_by('-paid_at')
        
        results = []
        for payment in payments:
            results.append({
                'id': payment.id,
                'payment_id': str(payment.payment_id),
                'employee_id': payment.employee.id,
                'employee_name': payment.employee.user.full_name or payment.employee.user.email,
                'payment_type': payment.payment_type,
                'gross_amount': float(payment.gross_amount),
                'net_amount': float(payment.net_amount),
                'payment_method': payment.payment_method,
                'payment_reference': payment.payment_reference,
                'payment_notes': payment.payment_notes,
                'period_start': payment.period_start,
                'period_end': payment.period_end,
                'paid_at': payment.paid_at,
                'status': payment.status
            })
        
        return Response({
            'results': results,
            'count': len(results)
        })
    
    @action(detail=False, methods=['post'])
    def execute_payment(self, request):
        """Ejecutar pago de liquidación"""
        settlement_id = request.data.get('settlement_id')
        payment_method = request.data.get('payment_method', 'cash')
        payment_reference = request.data.get('payment_reference', '')
        payment_notes = request.data.get('payment_notes', '')
        idempotency_key = request.data.get('idempotency_key')
        
        if not settlement_id:
            return Response({'error': 'settlement_id es requerido'}, status=400)
        
        try:
            with transaction.atomic():
                # Obtener settlement
                settlement = PayrollSettlement.objects.get(
                    id=settlement_id,
                    tenant=request.user.tenant
                )
                
                if settlement.status != 'READY':
                    return Response({
                        'error': f'Settlement debe estar en estado READY, actual: {settlement.status}'
                    }, status=400)
                
                # Verificar idempotencia
                if idempotency_key:
                    existing_payment = PayrollPayment.objects.filter(
                        idempotency_key=idempotency_key
                    ).first()
                    if existing_payment:
                        return Response({
                            'status': 'success',
                            'message': 'Pago ya procesado (idempotencia)',
                            'payment_id': existing_payment.id
                        })
                
                # Crear registro de pago
                payment = PayrollPayment.objects.create(
                    employee=settlement.employee,
                    tenant=settlement.tenant,
                    payment_type='PAYROLL',
                    gross_amount=settlement.gross_amount,
                    net_amount=settlement.net_amount,
                    payment_method=payment_method,
                    payment_reference=payment_reference,
                    payment_notes=payment_notes,
                    period_start=settlement.period_start,
                    period_end=settlement.period_end,
                    paid_by=request.user,
                    idempotency_key=idempotency_key
                )
                
                # Marcar settlement como pagado
                service = PayrollSettlementService()
                service.mark_as_paid(settlement)
                
                return Response({
                    'status': 'success',
                    'message': 'Pago ejecutado correctamente',
                    'payment_id': payment.id,
                    'settlement_id': settlement.id,
                    'amount_paid': float(payment.net_amount),
                    'paid_at': payment.paid_at.isoformat()
                })
                
        except PayrollSettlement.DoesNotExist:
            return Response({'error': 'Liquidación no encontrada'}, status=404)
        except Exception as e:
            return Response({'error': f'Error interno: {str(e)}'}, status=500)