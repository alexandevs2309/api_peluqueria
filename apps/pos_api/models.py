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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales', null=True, blank=True)
    employee = models.ForeignKey('employees_api.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    period = models.ForeignKey('employees_api.FortnightSummary', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
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
    closed = models.BooleanField(default=False)  # Útil para arqueo de caja

    class Meta:
        ordering = ['-date_time']
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'

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
    currency = models.CharField(max_length=3, default='USD')
    currency_symbol = models.CharField(max_length=5, default='$')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.0000)  # 0.1600 = 16%
    tax_included = models.BooleanField(default=False)  # Si el precio incluye impuestos
    receipt_template = models.TextField(default='default')
    receipt_footer = models.TextField(blank=True)
    auto_print_receipt = models.BooleanField(default=False)
    require_customer = models.BooleanField(default=False)
    allow_negative_stock = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'POS Configuration'
        verbose_name_plural = 'POS Configurations'