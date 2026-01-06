"""
Endpoint específico para pagos programados (empleados fijos/quincenales/mensuales)
NO modifica lógica ON_DEMAND existente
"""
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from decimal import Decimal
import uuid
import logging

from .models import Employee
from .payroll_models import PayrollPayment
from .payroll_periods import PayrollPeriod, PayrollPeriodManager
# ARCHIVO LEGACY - FortnightSummary eliminado
# Usar payroll_api.PayrollSettlement en su lugar
from .tax_calculator_factory import TaxCalculatorFactory
from apps.auth_api.permissions import IsClientAdmin

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsClientAdmin])
def pay_scheduled_payroll(request):
    """
    Ejecutar pago programado de un período específico
    
    Payload:
    {
        "employee_id": number,
        "period_id": number,
        "payment_date": "YYYY-MM-DD"
    }
    """
    employee_id = request.data.get('employee_id')
    period_id = request.data.get('period_id')
    payment_date = request.data.get('payment_date')
    
    # Validaciones básicas
    if not employee_id:
        return Response({'error': 'employee_id requerido'}, status=400)
    
    if not period_id:
        return Response({'error': 'period_id requerido'}, status=400)
    
    if not payment_date:
        payment_date = timezone.now().date()
    
    try:
        with transaction.atomic():
            # Validar empleado
            employee = Employee.objects.select_for_update().get(
                id=employee_id,
                tenant=request.user.tenant,
                is_active=True
            )
            
            # ARCHIVO LEGACY - FortnightSummary eliminado
            # Usar payroll_api.PayrollSettlement en su lugar
            return Response({
                'error': 'Endpoint legacy deshabilitado - usar payroll_api.PayrollSettlement'
            }, status=410)  # Gone
            
            # Validar estado PENDIENTE
            if period.is_paid:
                return Response({
                    'error': 'El período ya está pagado',
                    'paid_at': period.paid_at.isoformat() if period.paid_at else None
                }, status=409)
            
            # Validar idempotencia (evitar doble pago)
            idempotency_key = f"scheduled-{employee_id}-{period_id}"
            existing_payment = PayrollPayment.objects.filter(
                idempotency_key=idempotency_key
            ).first()
            
            if existing_payment:
                return Response({
                    'status': 'already_processed',
                    'message': 'Pago ya procesado anteriormente',
                    'payment_id': str(existing_payment.payment_id),
                    'paid_at': existing_payment.paid_at.isoformat()
                }, status=200)
            
            # Calcular montos usando lógica existente
            gross_amount = period.total_earnings
            if gross_amount <= 0:
                return Response({'error': 'No hay monto para pagar'}, status=400)
            
            # Aplicar descuentos legales
            country_code = getattr(employee.tenant, 'country', 'DO') or 'DO'
            tax_calculator = TaxCalculatorFactory.get_calculator(country_code)
            
            # Determinar si es fin de mes para descuentos
            is_month_end = tax_calculator.is_month_end_payment(year, fortnight)
            deductions = tax_calculator.calculate_deductions(gross_amount, employee, is_month_end)
            net_amount = tax_calculator.get_net_amount(gross_amount, deductions)
            
            # Crear PayrollPayment
            payment = PayrollPayment.objects.create(
                employee=employee,
                tenant=employee.tenant,
                period_year=year,
                period_index=fortnight,
                period_frequency='biweekly',
                period_start_date=_get_fortnight_start_date(year, fortnight),
                period_end_date=_get_fortnight_end_date(year, fortnight),
                payment_type='SCHEDULED',
                gross_amount=gross_amount,
                afp_deduction=deductions.get('afp', Decimal('0')),
                sfs_deduction=deductions.get('sfs', Decimal('0')),
                isr_deduction=deductions.get('isr', Decimal('0')),
                total_deductions=deductions.get('total', Decimal('0')),
                net_amount=net_amount,
                payment_method=request.data.get('payment_method', 'cash'),
                payment_reference=request.data.get('payment_reference', ''),
                payment_notes=request.data.get('payment_notes', ''),
                paid_by=request.user,
                idempotency_key=idempotency_key,
                status='COMPLETED'
            )
            
            # Marcar período como pagado
            period.is_paid = True
            period.paid_at = timezone.now()
            period.paid_by = request.user
            period.payment_method = payment.payment_method
            period.payment_reference = str(payment.payment_id)
            period.net_salary = net_amount
            period.amount_paid = net_amount
            period.afp_deduction = deductions.get('afp', Decimal('0'))
            period.sfs_deduction = deductions.get('sfs', Decimal('0'))
            period.isr_deduction = deductions.get('isr', Decimal('0'))
            period.total_deductions = deductions.get('total', Decimal('0'))
            period.save()
            
            # Generar recibo
            receipt_data = _generate_receipt(payment, employee, period)
            
            logger.info(f"Pago programado procesado: {payment.payment_id} - Empleado: {employee_id} - Monto: {net_amount}")
            
            return Response({
                'status': 'success',
                'message': 'Pago programado procesado correctamente',
                'payment_id': str(payment.payment_id),
                'employee_id': employee_id,
                'period_id': period_id,
                'gross_amount': float(gross_amount),
                'net_amount': float(net_amount),
                'deductions': {
                    'afp': float(deductions.get('afp', 0)),
                    'sfs': float(deductions.get('sfs', 0)),
                    'isr': float(deductions.get('isr', 0)),
                    'total': float(deductions.get('total', 0))
                },
                'paid_at': payment.paid_at.isoformat(),
                'receipt': receipt_data
            }, status=201)
            
    except Employee.DoesNotExist:
        return Response({'error': 'Empleado no encontrado'}, status=404)
    except Exception as e:
        logger.error(f"Error procesando pago programado: {str(e)}")
        return Response({'error': f'Error procesando pago: {str(e)}'}, status=500)

def _get_fortnight_start_date(year, fortnight):
    """Calcular fecha de inicio de quincena"""
    from datetime import datetime
    month = ((fortnight - 1) // 2) + 1
    is_first_half = (fortnight % 2) == 1
    
    if is_first_half:
        return datetime(year, month, 1).date()
    else:
        return datetime(year, month, 16).date()

def _get_fortnight_end_date(year, fortnight):
    """Calcular fecha de fin de quincena"""
    from datetime import datetime, timedelta
    month = ((fortnight - 1) // 2) + 1
    is_first_half = (fortnight % 2) == 1
    
    if is_first_half:
        return datetime(year, month, 15).date()
    else:
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        return (next_month - timedelta(days=1)).date()

def _generate_receipt(payment, employee, period):
    """Generar recibo de pago estructurado"""
    return {
        'receipt_number': f"REC-{payment.payment_id}",
        'employee': {
            'id': employee.id,
            'name': employee.user.full_name or employee.user.email,
            'email': employee.user.email
        },
        'period': {
            'year': payment.period_year,
            'fortnight': payment.period_index,
            'start_date': payment.period_start_date.isoformat(),
            'end_date': payment.period_end_date.isoformat()
        },
        'payment': {
            'payment_id': str(payment.payment_id),
            'payment_date': payment.paid_at.isoformat(),
            'payment_method': payment.payment_method,
            'payment_reference': payment.payment_reference
        },
        'amounts': {
            'gross_amount': float(payment.gross_amount),
            'deductions': {
                'afp': float(payment.afp_deduction),
                'sfs': float(payment.sfs_deduction),
                'isr': float(payment.isr_deduction),
                'total': float(payment.total_deductions)
            },
            'net_amount': float(payment.net_amount)
        },
        'generated_at': timezone.now().isoformat()
    }