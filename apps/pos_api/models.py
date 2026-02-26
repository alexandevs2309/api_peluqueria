from django.db import models 
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from apps.clients_api.models import Client
from apps.services_api.models import Service
from apps.inventory_api.models import Product
from apps.roles_api.models import Role
from django.utils.crypto import get_random_string


User = get_user_model()

class Sale(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('void', 'Void'),
        ('refunded', 'Refunded'),
    ]
    
    # ✅ CAMPO TENANT DIRECTO para filtrado eficiente
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE, related_name='sales', null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales', null=True, blank=True)
    employee = models.ForeignKey('employees_api.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    period = models.ForeignKey('employees_api.PayrollPeriod', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    cash_register = models.ForeignKey('CashRegister', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    date_time = models.DateTimeField(default=timezone.now)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=50, choices=[
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('transfer', 'Transfer'),
        ('mixed', 'Mixed'),
        ('other', 'Other')
    ], default='cash')
    closed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    
    # Snapshot de comisión (FASE 1 - Payroll Determinístico)
    commission_rate_snapshot = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Tasa de comisión vigente al momento de la venta'
    )
    commission_amount_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Monto de comisión calculado al momento de la venta'
    )
    
    # Campos de auditoría
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_updated')
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ['-date_time']
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'
        indexes = [
            models.Index(fields=['date_time', 'user']),
            models.Index(fields=['date_time', 'employee']),
            models.Index(fields=['status']),
        ]
    
    def save(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        
        # ✅ AUTO-ASIGNAR TENANT en creación
        if self.pk is None:
            if not self.tenant_id and self.user:
                self.tenant = self.user.tenant
            elif not self.tenant_id and self.employee:
                self.tenant = self.employee.tenant
            
            # Nueva venta: establecer status=confirmed por defecto
            if not self.status:
                self.status = 'confirmed'
            
            # NUEVO: Capturar snapshots de comisión al crear
            if self.employee and self.employee.commission_rate:
                self.commission_rate_snapshot = self.employee.commission_rate
                # Calcular monto de comisión
                from decimal import Decimal
                commission_rate = Decimal(str(self.employee.commission_rate)) / Decimal('100')
                self.commission_amount_snapshot = self.total * commission_rate
            
            return super().save(*args, **kwargs)
        
        # Venta existente: verificar inmutabilidad
        try:
            old_instance = Sale.objects.get(pk=self.pk)
        except Sale.DoesNotExist:
            return super().save(*args, **kwargs)
        
        # PROTECCIÓN CRÍTICA: Si snapshot existe, period es INMUTABLE
        if old_instance.commission_amount_snapshot is not None:
            if old_instance.period_id != self.period_id:
                raise ValidationError(
                    "No se puede cambiar el período de una venta con snapshot de comisión. "
                    "La comisión ya fue calculada y asignada."
                )
        
        # VALIDACIÓN: Evitar reasignación de period si está aprobado/pagado
        if old_instance.period_id != self.period_id and old_instance.period_id is not None:
            try:
                from apps.employees_api.earnings_models import PayrollPeriod
                old_period = PayrollPeriod.objects.get(pk=old_instance.period_id)
                if old_period.status in ['approved', 'paid']:
                    raise ValidationError(
                        f"No se puede reasignar la venta a otro período. "
                        f"El período actual está {old_period.get_status_display()}."
                    )
            except PayrollPeriod.DoesNotExist:
                pass
        
        # Permitir modificación solo si status=draft
        if old_instance.status != 'draft':
            # Permitir cambios SOLO en el campo status (para transiciones void/refunded)
            if old_instance.status != self.status:
                # Validar transiciones permitidas
                allowed_transitions = {
                    'confirmed': ['void', 'refunded'],
                    'void': [],
                    'refunded': [],
                }
                if self.status not in allowed_transitions.get(old_instance.status, []):
                    raise ValidationError(
                        f"No se puede cambiar status de '{old_instance.status}' a '{self.status}'"
                    )
                # Solo permitir cambio de status, nada más
                self.total = old_instance.total
                self.discount = old_instance.discount
                self.paid = old_instance.paid
                self.payment_method = old_instance.payment_method
                self.client_id = old_instance.client_id
                self.employee_id = old_instance.employee_id
                self.period_id = old_instance.period_id
                return super().save(*args, **kwargs)
            
            # Intentando modificar otros campos
            raise ValidationError(
                f"No se puede modificar una venta con status '{old_instance.status}'. "
                "Solo se permiten modificaciones en ventas con status 'draft'."
            )
        
        # Status es draft: permitir modificación
        return super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        from django.core.exceptions import ValidationError
        
        if self.status != 'draft':
            raise ValidationError(
                f"No se puede eliminar una venta con status '{self.status}'. "
                "Solo se permiten eliminaciones de ventas con status 'draft'."
            )
        return super().delete(*args, **kwargs)

class SaleDetail(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='details')
    
    # GenericForeignKey para referenciar Product o Service
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=False, validators=[])
    object_id = models.PositiveIntegerField(null=False, blank=False)
    content_object = GenericForeignKey('content_type', 'object_id')

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.content_type or not self.object_id:
            raise ValidationError('Both content type and object ID are required.')
    
    # Campos para almacenar datos al momento de la venta
    name = models.CharField(max_length=255)  # Nombre del producto/servicio
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Precio al momento de la venta
    

    class Meta:
        verbose_name = 'Sale Detail'
        verbose_name_plural = 'Sale Details'

    def __str__(self): 
        try:
            return f"{self.content_type.model}:{self.object_id} - {self.name}"
        except AttributeError:
            return f"Unknown type:{self.object_id} - {self.name}"
    
    @property
    def item_type(self):
        """Helper para obtener el tipo de item (product/service)"""
        try:
            return self.content_type.model
        except AttributeError:
            return 'unknown'

class Payment(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='payments')
    method = models.CharField(max_length=50, choices=[
            ('cash', 'Cash'),
            ('card', 'Card'),
            ('transfer', 'Transfer'),
            ('mixed', 'Mixed'),
            ('other', 'Other'),
        ], default='cash')
    amount = models.DecimalField(max_digits=10, decimal_places=2)

class CashRegister(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cash_registers')
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    initial_cash = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    final_cash = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_open = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-opened_at']
        indexes = [
            models.Index(fields=['user', 'opened_at']),
            models.Index(fields=['is_open']),
        ]
    
    def save(self, *args, **kwargs):
        # Asegurar que nunca sean null
        if self.initial_cash is None:
            self.initial_cash = 0.00
        if self.final_cash is None:
            self.final_cash = 0.00
        super().save(*args, **kwargs)
    
    @property
    def sales_amount(self):
        """Calcular ventas del día en el mismo tenant"""
        from django.db.models import Sum, Q
        if not self.opened_at:
            return 0.00
        
        # Incluir ventas con empleado del tenant y ventas sin empleado del usuario
        sales_total = Sale.objects.filter(
            Q(employee__tenant=self.user.tenant) | Q(user__tenant=self.user.tenant, employee__isnull=True),
            date_time__date=self.opened_at.date()
        ).aggregate(total=Sum('total'))['total'] or 0
        
        return float(sales_total)
    
    @property
    def display_amount(self):
        """Monto esperado en caja: inicial + ventas"""
        return float(self.initial_cash) + self.sales_amount

class CashCount(models.Model):
    """Arqueo de caja - conteo físico de dinero"""
    cash_register = models.ForeignKey(CashRegister, on_delete=models.CASCADE, related_name='cash_counts')
    denomination = models.DecimalField(max_digits=10, decimal_places=2)  # 1, 5, 10, 20, 50, 100
    count = models.IntegerField(default=0)  # cantidad de billetes/monedas
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # denominacion * count
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Cash Count'
        verbose_name_plural = 'Cash Counts'
        unique_together = ['cash_register', 'denomination']

class Promotion(models.Model):
    """Sistema de promociones y descuentos"""
    PROMOTION_TYPES = [
        ('percentage', 'Percentage Discount'),
        ('fixed', 'Fixed Amount Discount'),
        ('buy_x_get_y', 'Buy X Get Y Free'),
        ('combo', 'Combo Offer')
    ]
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=PROMOTION_TYPES)
    conditions = models.JSONField(default=dict)  # Condiciones específicas
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    max_uses = models.IntegerField(null=True, blank=True)  # Límite de usos
    current_uses = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Promotion'
        verbose_name_plural = 'Promotions'
        ordering = ['-created_at']

class Receipt(models.Model):
    """Recibos generados"""
    sale = models.OneToOneField(Sale, on_delete=models.CASCADE, related_name='receipt')
    receipt_number = models.CharField(max_length=50, unique=True)
    template_used = models.CharField(max_length=100, default='default')
    generated_at = models.DateTimeField(auto_now_add=True)
    printed_count = models.IntegerField(default=0)
    last_printed = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Receipt'
        verbose_name_plural = 'Receipts'
        ordering = ['-generated_at']

class PosConfiguration(models.Model):
    """Configuración del POS por tenant"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pos_config')
    business_name = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    currency = models.CharField(max_length=3, default='USD')
    currency_symbol = models.CharField(max_length=5, default='$')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.0000)
    tax_included = models.BooleanField(default=False)
    receipt_template = models.TextField(default='default')
    receipt_footer = models.TextField(blank=True)
    auto_print_receipt = models.BooleanField(default=False)
    require_customer = models.BooleanField(default=False)
    allow_negative_stock = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'POS Configuration'
        verbose_name_plural = 'POS Configurations'