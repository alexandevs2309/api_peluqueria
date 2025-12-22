"""
Servicio centralizado para cálculo de balance de empleados

MODELO ARQUITECTÓNICO:
balance = sum(Earning.amount) - sum(PayrollPayment.net_amount)

- Balance NO se persiste
- Se calcula bajo demanda
- Usado por preview y pago final
"""
from django.db.models import Sum
from decimal import Decimal
from ..earnings_models import Earning
from ..payroll_models import PayrollPayment


class EmployeeBalanceService:
    """Servicio centralizado para cálculo de balance de empleados"""
    
    @staticmethod
    def get_balance(employee_id):
        """
        Calcula balance disponible: sum(earnings) - sum(payments)
        
        Args:
            employee_id: ID del empleado
            
        Returns:
            Decimal: Balance disponible
        """
        # Sumar todas las ganancias
        total_earnings = Earning.objects.filter(
            employee_id=employee_id
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Sumar todos los pagos realizados (monto neto)
        total_payments = PayrollPayment.objects.filter(
            employee_id=employee_id
        ).aggregate(
            total=Sum('net_amount')
        )['total'] or Decimal('0.00')
        
        return total_earnings - total_payments
    
    @staticmethod
    def get_balance_breakdown(employee_id):
        """
        Obtiene desglose completo del balance
        
        Returns:
            dict: {
                'total_earnings': Decimal,
                'total_payments': Decimal, 
                'available_balance': Decimal
            }
        """
        total_earnings = Earning.objects.filter(
            employee_id=employee_id
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        total_payments = PayrollPayment.objects.filter(
            employee_id=employee_id
        ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')
        
        return {
            'total_earnings': total_earnings,
            'total_payments': total_payments,
            'available_balance': total_earnings - total_payments
        }