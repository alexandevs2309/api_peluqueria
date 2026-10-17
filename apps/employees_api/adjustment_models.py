from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class CommissionAdjustment(models.Model):
    """
    Ajustes de comisión (positivos o negativos)
    Usado para refunds, bonos, penalizaciones, etc.
    """
    
    REASON_CHOICES = [
        ('refund', 'Reembolso de venta'),
        ('partial_refund', 'Reembolso parcial'),
        ('bonus', 'Bono adicional'),
        ('penalty', 'Penalización'),
        ('correction', 'Corrección contable'),
        ('other', 'Otro'),
    ]
    
    sale = models.ForeignKey(
        'pos_api.Sale',
        on_delete=models.PROTECT,
        related_name='commission_adjustments',
        null=True,
        blank=True,
        help_text='Venta relacionada (si aplica)'
    )

    # Línea de venta origen del ajuste. Permite un ajuste por barbero en
    # ventas con varios servicios. NULL = ajuste a nivel de venta (histórico).
    sale_detail = models.ForeignKey(
        'pos_api.SaleDetail',
        on_delete=models.PROTECT,
        related_name='commission_adjustments',
        null=True,
        blank=True,
        help_text='Línea de venta origen (comisión por servicio)'
    )

    # Clave de idempotencia del reembolso. Reintentar el mismo reembolso con
    # la misma clave no genera ajustes duplicados.
    idempotency_key = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text='Clave de idempotencia para reembolsos repetidos'
    )
    
    payroll_period = models.ForeignKey(
        'employees_api.PayrollPeriod',
        on_delete=models.PROTECT,
        related_name='commission_adjustments'
    )
    
    employee = models.ForeignKey(
        'employees_api.Employee',
        on_delete=models.PROTECT,
        related_name='commission_adjustments'
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Monto del ajuste (negativo para deducciones)'
    )
    
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        default='other'
    )
    
    description = models.TextField(
        blank=True,
        help_text='Descripción detallada del ajuste'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='commission_adjustments_created'
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    
    # Multi-tenant
    tenant = models.ForeignKey(
        'tenants_api.Tenant',
        on_delete=models.CASCADE,
        related_name='commission_adjustments'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payroll_period', 'employee']),
            models.Index(fields=['sale']),
            models.Index(fields=['sale_detail']),
            models.Index(fields=['tenant', 'created_at']),
        ]
        constraints = [
            # Un reembolso TOTAL por línea de venta (o por venta cuando no hay
            # línea). Una venta con 2 barberos genera 2 ajustes distintos y una
            # repetición sobre la misma línea no se duplica.
            # Los reembolsos parciales se protegen con `idempotency_key` y con el
            # tope de `Sale.amount_refunded`.
            models.UniqueConstraint(
                fields=['sale', 'sale_detail', 'reason'],
                condition=models.Q(reason='refund'),
                name='unique_refund_per_sale_line'
            ),
            # Idempotencia explícita para reembolsos repetidos.
            models.UniqueConstraint(
                fields=['idempotency_key'],
                condition=models.Q(idempotency_key__isnull=False),
                name='unique_adjustment_idempotency_key'
            ),
        ]
    
    def __str__(self):
        return f"Ajuste {self.get_reason_display()} - {self.employee} - ${self.amount}"
    
    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        
        # Validar que el período no esté finalizado
        if hasattr(self.payroll_period, 'is_finalized') and self.payroll_period.is_finalized:
            raise ValidationError(
                "No se pueden crear ajustes en un período finalizado"
            )
        
        # Heredar tenant del empleado
        if not self.tenant_id:
            self.tenant = self.employee.tenant
        
        super().save(*args, **kwargs)
