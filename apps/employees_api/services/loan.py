"""
Servicio de préstamos para empleados

MODELO ARQUITECTÓNICO RESPETADO:
- Los préstamos NO afectan ventas, earnings ni balance
- Los préstamos SOLO se aplican en el momento del pago
- Preview no persiste datos
- El backend recalcula todo en el pago final
"""
from django.db import transaction
from decimal import Decimal
from ..advance_loans import AdvanceLoan, LoanPayment
from datetime import date
import logging

logger = logging.getLogger(__name__)


class LoanService:
    """Servicio de préstamos que respeta el modelo arquitectónico"""
    
    @staticmethod
    def preview_deductions(employee_id, available_balance):
        """
        Calcula preview de descuentos de préstamos SIN persistir datos
        
        Args:
            employee_id: ID del empleado
            available_balance: Balance disponible del empleado
            
        Returns:
            dict: {
                'total_deduction': Decimal,
                'loans': [{'loan_id', 'amount', 'remaining_balance'}],
                'can_apply': bool
            }
        """
        # Obtener préstamos activos (SOLO LECTURA)
        active_loans = AdvanceLoan.objects.filter(
            employee_id=employee_id,
            status='active',
            remaining_balance__gt=0
        ).order_by('first_payment_date')
        
        if not active_loans.exists():
            return {
                'total_deduction': Decimal('0'),
                'loans': [],
                'can_apply': True
            }
        
        # Calcular descuentos sin persistir
        total_deduction = Decimal('0')
        loan_details = []
        
        for loan in active_loans:
            # Calcular descuento: min(cuota mensual, saldo restante)
            deduction = min(loan.monthly_payment, loan.remaining_balance)
            
            if deduction > 0:
                total_deduction += deduction
                loan_details.append({
                    'loan_id': loan.id,
                    'loan_type': loan.get_loan_type_display(),
                    'amount': float(deduction),
                    'remaining_balance': float(loan.remaining_balance),
                    'monthly_payment': float(loan.monthly_payment)
                })
        
        # Verificar si se puede aplicar (balance suficiente)
        can_apply = available_balance >= total_deduction
        
        return {
            'total_deduction': total_deduction,
            'loans': loan_details,
            'can_apply': can_apply,
            'balance_after_deduction': available_balance - total_deduction if can_apply else available_balance
        }
    
    @staticmethod
    @transaction.atomic
    def apply_deductions(payment, employee_id):
        """
        Aplica descuentos de préstamos DENTRO de transacción de pago
        
        Args:
            payment: Instancia de PayrollPayment
            employee_id: ID del empleado
            
        Returns:
            dict: {
                'total_deducted': Decimal,
                'deductions': [{'loan_id', 'amount_deducted', 'new_balance'}]
            }
        """
        # Obtener préstamos activos con lock para concurrencia
        active_loans = AdvanceLoan.objects.select_for_update().filter(
            employee_id=employee_id,
            status='active',
            remaining_balance__gt=0
        ).order_by('first_payment_date')
        
        if not active_loans.exists():
            return {
                'total_deducted': Decimal('0'),
                'deductions': []
            }
        
        total_deducted = Decimal('0')
        deduction_details = []
        
        for loan in active_loans:
            # Calcular descuento real
            deduction = min(loan.monthly_payment, loan.remaining_balance)
            
            if deduction > 0:
                # Crear registro de pago del préstamo
                payment_number = loan.payments.count() + 1
                
                LoanPayment.objects.create(
                    loan=loan,
                    payment_date=date.today(),
                    amount=deduction,
                    payment_number=payment_number,
                    payroll_payment=None  # No usar FortnightSummary, usar PayrollPayment
                )
                
                # Actualizar saldo del préstamo
                loan.remaining_balance -= deduction
                
                # Marcar como completado si saldo <= 0
                if loan.remaining_balance <= 0:
                    loan.status = 'completed'                
                loan.save()
                
                total_deducted += deduction
                deduction_details.append({
                    'loan_id': loan.id,
                    'amount_deducted': float(deduction),
                    'new_balance': float(loan.remaining_balance),
                    'status': loan.status
                })
                
                logger.info(f"Préstamo {loan.id}: deducido ${deduction}, nuevo saldo ${loan.remaining_balance}")
        
        return {
            'total_deducted': total_deducted,
            'deductions': deduction_details
        }