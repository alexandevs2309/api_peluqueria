"""
Modelos para pagos reales de nómina (facturación)
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid

class PayrollPayment(models.Model):
    """
    Registro de pago real de nómina - BASE PARA FACTURACIÓN
    Solo se crea cuando se ejecuta un pago real
    """
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('COMPLETED', 'Completado'),
        ('FAILED', 'Fallido')
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('fixed_salary', 'Sueldo Fijo'),
        ('commission', 'Comisión'),
        ('mixed', 'Mixto'),
        ('bonus', 'Bono'),
        ('adjustment', 'Ajuste'),
        ('SCHEDULED', 'Pago Programado'),
        ('PAYROLL', 'Nómina')
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Efectivo'),
        ('transfer', 'Transferencia'),
        ('check', 'Cheque'),
        ('other', 'Otro')
    ]
    
    # Identificación única e idempotencia
    payment_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    idempotency_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    
    # Empleado y tenant
    employee = models.ForeignKey(
        'employees_api.Employee',
        on_delete=models.CASCADE,
        related_name='payroll_payments'
    )
    tenant = models.ForeignKey(
        'tenants_api.Tenant',
        on_delete=models.CASCADE,
        related_name='payroll_payments'
    )
    
    # Período pagado
    period_year = models.IntegerField()
    period_index = models.IntegerField()  # Índice según frecuencia
    period_frequency = models.CharField(max_length=10)  # daily, weekly, biweekly, monthly
    period_start_date = models.DateField()
    period_end_date = models.DateField()
    
    # Tipo de pago
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    
    # Montos
    gross_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Monto bruto antes de descuentos"
    )
    
    # Descuentos legales
    afp_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    sfs_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    isr_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    loan_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Monto neto pagado
    net_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Monto neto pagado al empleado"
    )
    
    # Datos del pago
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_reference = models.CharField(max_length=100, blank=True)
    payment_notes = models.TextField(blank=True)
    
    # Trazabilidad para comisiones
    commission_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Porcentaje de comisión aplicado"
    )
    commission_base_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Monto base para cálculo de comisión"
    )
    
    # Auditoría
    paid_at = models.DateTimeField(default=timezone.now)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-paid_at']
        indexes = [
            models.Index(fields=['employee', 'period_year', 'period_index']),
            models.Index(fields=['tenant', 'paid_at']),
            models.Index(fields=['payment_type']),
            models.Index(fields=['idempotency_key']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Pago {self.payment_id} - {self.employee} - ${self.net_amount}"

class PayrollPaymentSale(models.Model):
    """Relación entre pagos de nómina y ventas (para comisiones)"""
    
    payment = models.ForeignKey(
        PayrollPayment,
        on_delete=models.CASCADE,
        related_name='sales'
    )
    sale = models.ForeignKey(
        'pos_api.Sale',
        on_delete=models.CASCADE,
        related_name='payroll_payments'
    )
    
    # Datos de la venta al momento del pago
    sale_total = models.DecimalField(max_digits=10, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['payment', 'sale']
        indexes = [
            models.Index(fields=['payment']),
            models.Index(fields=['sale']),
        ]
    
    def __str__(self):
        return f"Pago {self.payment.payment_id} - Venta {self.sale.id}"