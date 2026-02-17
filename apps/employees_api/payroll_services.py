from decimal import Decimal
from django.db.models import Sum


class PayrollCalculationService:
    """Servicio para cálculo determinístico de nómina desde snapshots"""
    
    @staticmethod
    def calculate_from_snapshots(period):
        """
        Calcula comisiones exclusivamente desde snapshots
        NO usa Employee como fuente viva
        
        Args:
            period: Instancia de PayrollPeriod
            
        Returns:
            dict con totales calculados
        """
        from apps.pos_api.models import Sale
        from apps.employees_api.adjustment_models import CommissionAdjustment
        
        # 1. Sumar comisiones desde snapshots de ventas
        sales_commission = Sale.objects.filter(
            employee=period.employee,
            date_time__date__gte=period.period_start,
            date_time__date__lte=period.period_end,
            status='confirmed',
            commission_amount_snapshot__isnull=False,
            user__tenant=period.employee.tenant  # FIX 4: Filtro explícito por tenant
        ).aggregate(
            total=Sum('commission_amount_snapshot')
        )['total'] or Decimal('0.00')
        
        # 2. Sumar ajustes (positivos y negativos)
        adjustments_total = CommissionAdjustment.objects.filter(
            payroll_period=period
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        # 3. Total de comisiones
        total_commission = sales_commission + adjustments_total
        
        # 4. Salario base (si aplica) - usar datos del empleado directamente
        payment_type = period.employee.payment_type
        fixed_salary = period.employee.fixed_salary
        
        base_salary = Decimal('0.00')
        if payment_type in ['fixed', 'mixed']:
            if period.period_type == 'monthly':
                base_salary = fixed_salary
            elif period.period_type == 'biweekly':
                base_salary = fixed_salary / 2
            elif period.period_type == 'weekly':
                base_salary = fixed_salary / 4
        
        return {
            'base_salary': base_salary,
            'commission_earnings': total_commission,
            'sales_commission': sales_commission,
            'adjustments': adjustments_total,
            'gross_amount': base_salary + total_commission,
        }
    
    @staticmethod
    def apply_calculation_to_period(period, calculation_result):
        """
        Aplica resultado de cálculo al período
        
        Args:
            period: Instancia de PayrollPeriod
            calculation_result: dict con resultados
        """
        period.base_salary = calculation_result['base_salary']
        period.commission_earnings = calculation_result['commission_earnings']
        period.gross_amount = calculation_result['gross_amount']
        
        # Calcular deducciones y neto
        deductions = period.deductions.all()
        period.deductions_total = sum(d.amount for d in deductions)
        period.net_amount = period.gross_amount - period.deductions_total
