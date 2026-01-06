"""
Dominio de nómina - Modelos core
Separación clara: Configuración → Deuda → Liquidación → Pago

USA modelo Earning existente, NO lo duplica
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta, date
import uuid

class PayrollSettlement(models.Model):
    """
    CORAZÓN DEL SISTEMA: Liquidación por período
    Calcula cuánto se debe, NO ejecuta pagos
    """
    
    FREQUENCY_CHOICES = [
        ('daily', 'Diario'),
        ('weekly', 'Semanal'), 
        ('biweekly', 'Quincenal'),
        ('monthly', 'Mensual')
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Abierto - Acumulando deuda'),
        ('READY', 'Listo para pago'),
        ('PAID', 'Pagado')
    ]
    
    # Identificación única
    settlement_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Empleado y configuración
    employee = models.ForeignKey('employees_api.Employee', on_delete=models.CASCADE, related_name='settlements')
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE)
    
    # Período de liquidación
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()
    period_year = models.IntegerField()
    period_index = models.IntegerField()  # 1-365, 1-52, 1-24, 1-12 según frecuencia
    
    # Estado de liquidación
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN')
    
    # Montos liquidados (calculados, NO pagados)
    fixed_salary_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Descuentos legales
    afp_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    sfs_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    isr_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Monto neto liquidado
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)  # Cuando se marca READY
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ('employee', 'frequency', 'period_year', 'period_index')
        ordering = ['-period_year', '-period_index']
        indexes = [
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['period_year', 'period_index']),
        ]
    
    def __str__(self):
        return f"Settlement {self.settlement_id} - {self.employee} - {self.frequency} {self.period_year}/{self.period_index}"
    
    @property
    def can_pay(self):
        """Determina si se puede pagar según el período contable"""
        today = timezone.now().date()
        return today >= self.period_end
    
    @property
    def pay_block_reason(self):
        """Razón por la cual no se puede pagar"""
        if self.can_pay:
            return None
        return "El período de pago aún no ha finalizado"
    
    @property
    def loan_deductions(self):
        """Calcula deducciones de préstamos dinámicamente"""
        return self.total_deductions - self.afp_deduction - self.sfs_deduction - self.isr_deduction

class SettlementEarning(models.Model):
    """
    Relación entre liquidación y earnings
    Trazabilidad de qué deuda se incluye en cada liquidación
    USA el modelo Earning existente de employees_api
    """
    settlement = models.ForeignKey(PayrollSettlement, on_delete=models.CASCADE, related_name='earnings')
    earning = models.ForeignKey('employees_api.Earning', on_delete=models.CASCADE)  # Usa modelo existente
    
    # Datos del earning al momento de liquidación
    earning_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('settlement', 'earning')
    
    def __str__(self):
        return f"Settlement {self.settlement.settlement_id} - Earning {self.earning.id}"