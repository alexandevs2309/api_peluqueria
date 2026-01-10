from django.db import models
from decimal import Decimal

class MonthlyLegalDeductions(models.Model):
    """
    Control mensual de descuentos legales para cumplir normativa RD
    Garantiza aplicación UNA VEZ por mes fiscal
    """
    employee = models.ForeignKey('employees_api.Employee', on_delete=models.CASCADE, related_name='monthly_deductions')
    year = models.IntegerField()
    month = models.IntegerField()
    
    # Acumulación mensual
    total_monthly_gross = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Descuentos aplicados (UNA VEZ por mes)
    afp_applied = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    sfs_applied = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    isr_applied = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Referencia al settlement donde se aplicaron
    applied_in_settlement = models.ForeignKey('payroll_api.PayrollSettlement', on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('employee', 'year', 'month')
        indexes = [
            models.Index(fields=['employee', 'year', 'month']),
        ]
    
    def __str__(self):
        return f"Descuentos {self.employee} - {self.month}/{self.year}"