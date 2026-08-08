from decimal import Decimal
from django.utils import timezone
from apps.employees_api.compensation_models import EmployeeCompensationHistory


class SaleCommissionService:
    """Servicio para calcular y guardar snapshot de comisión en ventas"""
    
    @staticmethod
    def calculate_commission_snapshot(employee, sale_total, sale_date=None):
        """
        Calcula comisión usando historial de compensación vigente
        
        Args:
            employee: Instancia de Employee
            sale_total: Decimal con total de la venta
            sale_date: Fecha de la venta (default: hoy)
            
        Returns:
            tuple: (commission_rate, commission_amount)
        """
        if sale_date is None:
            sale_date = timezone.now().date()
        
        # Obtener compensación vigente en la fecha de venta
        compensation = EmployeeCompensationHistory.get_active_compensation(
            employee=employee,
            date=sale_date
        )
        
        if compensation:
            # Usar tasa del historial
            commission_rate = compensation.commission_rate
        else:
            # Fallback: usar tasa actual del empleado
            commission_rate = employee.commission_rate
        
        # Calcular monto de comisión
        if employee.payment_type in ['commission', 'mixed']:
            commission_amount = (sale_total * commission_rate) / Decimal('100')
        else:
            commission_amount = Decimal('0.00')
        
        return commission_rate, commission_amount
    
    @staticmethod
    def apply_commission_snapshot(sale, employee):
        """
        Aplica snapshot de comisión a una venta
        
        Args:
            sale: Instancia de Sale (sin guardar)
            employee: Instancia de Employee
        """
        if employee and employee.payment_type in ['commission', 'mixed']:
            rate, amount = SaleCommissionService.calculate_commission_snapshot(
                employee=employee,
                sale_total=sale.total,
                sale_date=sale.date_time.date() if sale.date_time else None
            )
            sale.commission_rate_snapshot = rate
            sale.commission_amount_snapshot = amount
        else:
            sale.commission_rate_snapshot = Decimal('0.00')
            sale.commission_amount_snapshot = Decimal('0.00')
