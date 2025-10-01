from django.db import models 
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from apps.clients_api.models import Client
from apps.services_api.models import Service
from apps.inventory_api.models import Product
from apps.roles_api.models import Role


User = get_user_model()

class Sale(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales')
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
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
    closed = models.BooleanField(default=False) # util para arqueo de caja

    class Meta:
        ordering = ['-date_time']
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'

class SaleDetail(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='details')
    
    # GenericForeignKey para referenciar Product o Service
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Campos para almacenar datos al momento de la venta
    name = models.CharField(max_length=255)  # Nombre del producto/servicio
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Precio al momento de la venta
    

    class Meta:
        verbose_name = 'Sale Detail'
        verbose_name_plural = 'Sale Details'

    def __str__(self): 
        return f"{self.content_type.model}:{self.object_id} - {self.name}"
    
    @property
    def item_type(self):
        """Helper para obtener el tipo de item (product/service)"""
        return self.content_type.model

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