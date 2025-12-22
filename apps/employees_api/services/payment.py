"""
Servicio de pago endurecido con idempotencia y transacciones atómicas

GARANTÍAS:
- Idempotencia usando idempotency_key
- Transacciones atómicas
- Recálculo de balance dentro de transacción
- Estados claros (PENDING, COMPLETED, FAILED)
"""
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from ..payroll_models import PayrollPayment
from ..models import Employee
from .balance import EmployeeBalanceService
from .loan import LoanService
from ..advance_loans import LoanDeduction
import logging

logger = logging.getLogger(__name__)


class PaymentService:
    """Servicio de pago endurecido contra concurrencia"""
    
    @staticmethod
    @transaction.atomic
    def process_payment(employee_id, requested_amount, payment_data, idempotency_key):
        """
        Procesa pago de empleado con garantías de idempotencia y atomicidad
        
        Args:
            employee_id: ID del empleado
            requested_amount: Monto solicitado (NO confiable)
            payment_data: Datos del pago (método, referencia, etc.)
            idempotency_key: Clave de idempotencia única
            
        Returns:
            dict: Resultado del pago con estado y detalles
        """
        # 1. VERIFICAR IDEMPOTENCIA
        if idempotency_key:
            existing_payment = PayrollPayment.objects.filter(
                idempotency_key=idempotency_key
            ).first()
            
            if existing_payment:
                if existing_payment.status == 'COMPLETED':
                    return {
                        'status': 'already_processed',
                        'payment_id': str(existing_payment.payment_id),
                        'message': 'Pago ya procesado exitosamente',
                        'amount': float(existing_payment.net_amount)
                    }
                elif existing_payment.status == 'PENDING':
                    return {
                        'status': 'processing',
                        'payment_id': str(existing_payment.payment_id),
                        'message': 'Pago en proceso'
                    }
                elif existing_payment.status == 'FAILED':
                    # Permitir retry de pagos fallidos
                    existing_payment.delete()
        
        # 2. OBTENER EMPLEADO CON LOCK
        try:
            employee = Employee.objects.select_for_update().get(
                id=employee_id,
                is_active=True
            )
        except Employee.DoesNotExist:
            return {
                'status': 'error',
                'message': 'Empleado no encontrado o inactivo'
            }
        
        # 3. RECALCULAR BALANCE DENTRO DE TRANSACCIÓN
        available_balance = EmployeeBalanceService.get_balance(employee.id)
        
        # 4. VALIDAR BALANCE POSITIVO (INVARIANTE 6)
        if available_balance <= 0:
            return {
                'status': 'error',
                'message': 'No hay balance disponible para pago',
                'available_balance': float(available_balance)
            }
        
        # 5. VALIDAR BALANCE SUFICIENTE
        if requested_amount > available_balance:
            return {
                'status': 'error',
                'message': 'Balance insuficiente',
                'available_balance': float(available_balance),
                'requested_amount': float(requested_amount)
            }
        
        if requested_amount <= 0:
            return {
                'status': 'error',
                'message': 'Monto debe ser mayor a 0'
            }
        
        # VALIDAR CAJA ABIERTA PARA PAGOS EN EFECTIVO
        if payment_data.get('payment_method') == 'cash':
            from apps.pos_api.models import CashRegister
            open_register = CashRegister.objects.filter(
                user__tenant=employee.tenant,
                is_open=True
            ).first()
            
            if not open_register:
                return {
                    'status': 'error',
                    'message': 'No hay caja registradora abierta para procesar pagos en efectivo'
                }
        
        actual_amount = requested_amount
        
        # 6. APLICAR DEDUCCIONES DE PRÉSTAMOS
        loan_result = LoanService.apply_deductions(
            payment=None,  # Se creará después
            employee_id=employee.id
        )
        
        total_loan_deductions = loan_result['total_deducted']
        net_amount = actual_amount - total_loan_deductions
        
        # Validar que el neto sea positivo
        if net_amount < 0:
            return {
                'status': 'error',
                'message': 'Deducciones de préstamos exceden el monto disponible',
                'loan_deductions': float(total_loan_deductions),
                'available': float(actual_amount)
            }
        
        # 7. CREAR PAGO EN ESTADO PENDING
        try:
            payment = PayrollPayment.objects.create(
                employee=employee,
                tenant=employee.tenant,
                idempotency_key=idempotency_key,
                status='PENDING',
                
                # Período actual (simplificado)
                period_year=timezone.now().year,
                period_index=1,
                period_frequency='on_demand',
                period_start_date=timezone.now().date(),
                period_end_date=timezone.now().date(),
                
                # Tipo y montos
                payment_type='commission',
                gross_amount=actual_amount,
                loan_deductions=total_loan_deductions,
                total_deductions=total_loan_deductions,
                net_amount=net_amount,
                
                # Datos del pago
                payment_method=payment_data.get('payment_method', 'cash'),
                payment_reference=payment_data.get('payment_reference', ''),
                payment_notes=payment_data.get('payment_notes', ''),
                paid_by=payment_data.get('paid_by')
            )
            
            # 8. REGISTRAR DEDUCCIONES DE PRÉSTAMOS
            for deduction in loan_result['deductions']:
                LoanDeduction.objects.create(
                    payroll_payment=payment,
                    loan_id=deduction['loan_id'],
                    amount=Decimal(str(deduction['amount_deducted'])),
                    loan_balance_after=Decimal(str(deduction['new_balance']))
                )
            
            # 9. MARCAR COMO COMPLETADO
            payment.status = 'COMPLETED'
            payment.paid_at = timezone.now()
            payment.save()
            
            logger.info(f"Pago procesado exitosamente: {payment.payment_id}")
            
            return {
                'status': 'success',
                'payment_id': str(payment.payment_id),
                'message': 'Pago procesado exitosamente',
                'gross_amount': float(actual_amount),
                'loan_deductions': float(total_loan_deductions),
                'net_amount': float(net_amount),
                'new_balance': float(available_balance - actual_amount),
                'loan_details': loan_result['deductions']
            }
            
        except Exception as e:
            logger.error(f"Error procesando pago: {str(e)}")
            
            # Marcar como fallido si el pago se creó
            if 'payment' in locals():
                payment.status = 'FAILED'
                payment.save()
            
            return {
                'status': 'error',
                'message': f'Error procesando pago: {str(e)}'
            }