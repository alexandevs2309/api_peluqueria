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

# === MODELOS EXISTENTES ===

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
    applied_in_settlement = models.ForeignKey('PayrollSettlement', on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('employee', 'year', 'month')
        indexes = [
            models.Index(fields=['employee', 'year', 'month']),
        ]
    
    def __str__(self):
        return f"Descuentos {self.employee} - {self.month}/{self.year}"

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
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text='Salario por comisión calculado')
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text='Salario total bruto (fijo + comisión)')
    
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
    
    # Propiedades con naming correcto para salarios
    @property
    def commission_salary_amount(self):
        """Alias con naming correcto: salario por comisión"""
        return self.commission_amount
    
    @property
    def total_salary_amount(self):
        """Alias con naming correcto: salario total bruto"""
        return self.gross_amount

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

# === NUEVA ARQUITECTURA PROFESIONAL ===

class PayrollPeriod(models.Model):
    """
    Períodos de nómina - Fuente de verdad temporal
    """
    FREQUENCY_CHOICES = [
        ('daily', 'Diario'),
        ('weekly', 'Semanal'), 
        ('biweekly', 'Quincenal'),
        ('monthly', 'Mensual')
    ]
    
    STATUS_CHOICES = [
        ('OPEN', 'Abierto'),
        ('CLOSED', 'Cerrado'),
        ('PAID', 'Pagado')
    ]
    
    period_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE)
    
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()
    period_year = models.IntegerField()
    period_index = models.IntegerField()  # 1-365, 1-52, 1-24, 1-12
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN')
    
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ('tenant', 'frequency', 'period_year', 'period_index')
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['period_year', 'period_index']),
        ]
    
    def __str__(self):
        return f"Period {self.frequency} {self.period_year}/{self.period_index}"

class PayrollCalculation(models.Model):
    """
    Cálculos de nómina versionados y auditables
    """
    calculation_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    employee = models.ForeignKey('employees_api.Employee', on_delete=models.CASCADE)
    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE)
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE)
    
    # Versioning para recálculos
    version = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)
    
    # Breakdown completo en JSON
    calculation_breakdown = models.JSONField(default=dict, help_text='Detalle completo del cálculo')
    
    # Campos calculados (desnormalizados para performance)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    commission_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    bonuses_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    gross_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    legal_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    loan_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Auditoría
    calculated_at = models.DateTimeField(auto_now_add=True)
    calculated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ('employee', 'period', 'version')
        indexes = [
            models.Index(fields=['employee', 'period', 'is_current']),
            models.Index(fields=['tenant', 'period']),
        ]
    
    def save(self, *args, **kwargs):
        # Invalidar versiones anteriores
        if self.is_current:
            PayrollCalculation.objects.filter(
                employee=self.employee,
                period=self.period,
                is_current=True
            ).update(is_current=False)
        super().save(*args, **kwargs)

class PayrollPaymentNew(models.Model):
    """
    Pagos ejecutados - Separado de cálculos
    """
    payment_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    calculation = models.OneToOneField(PayrollCalculation, on_delete=models.CASCADE, related_name='payment_new')
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE)
    
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=50, default='cash')
    payment_reference = models.CharField(max_length=100, blank=True)
    
    paid_at = models.DateTimeField(auto_now_add=True)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='new_payroll_payments')
    
    # Auditoría de pagos
    payment_notes = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'paid_at']),
        ]