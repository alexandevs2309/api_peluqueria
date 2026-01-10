"""
Nuevos modelos de nómina - Arquitectura profesional
Reemplaza apps/payroll_api/models.py
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid

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

class PayrollPayment(models.Model):
    """
    Pagos ejecutados - Separado de cálculos
    """
    payment_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    calculation = models.OneToOneField(PayrollCalculation, on_delete=models.CASCADE, related_name='payment')
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE)
    
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=50, default='cash')
    payment_reference = models.CharField(max_length=100, blank=True)
    
    paid_at = models.DateTimeField(auto_now_add=True)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Auditoría de pagos
    payment_notes = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'paid_at']),
            models.Index(fields=['calculation__employee', 'paid_at']),
        ]