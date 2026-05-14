from django.db import models
from django.conf import settings
from django.core import signing
from apps.subscriptions_api.models import UserSubscription
import uuid

class EncryptedFieldMixin:
    """Mixin que encripta/desencripta campos automaticamente usando SECRET_KEY"""

    @staticmethod
    def encrypt(value):
        if not value:
            return value
        return signing.dumps(value, salt="payment_provider", compress=True)

    @staticmethod
    def decrypt(value):
        if not value:
            return value
        try:
            return signing.loads(value, salt="payment_provider")
        except (signing.BadSignature, signing.SignatureExpired):
            return value  # Devuelve raw si no se puede desencriptar

class PaymentProvider(models.Model, EncryptedFieldMixin):
    PROVIDER_CHOICES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('manual', 'Manual'),
    ]
    
    name = models.CharField(max_length=50, choices=PROVIDER_CHOICES, unique=True)
    is_active = models.BooleanField(default=True)
    api_key = models.CharField(max_length=512, blank=True, editable=False,
                                help_text="Encriptado automaticamente. No modificar manualmente.")
    webhook_secret = models.CharField(max_length=512, blank=True, editable=False,
                                      help_text="Encriptado automaticamente. No modificar manualmente.")
    
    def save(self, *args, **kwargs):
        if self.api_key and not self.api_key.startswith('gAAAAA'):
            self.api_key = self.encrypt(self.api_key)
        if self.webhook_secret and not self.webhook_secret.startswith('gAAAAA'):
            self.webhook_secret = self.encrypt(self.webhook_secret)
        super().save(*args, **kwargs)
    
    def get_api_key(self):
        return self.decrypt(self.api_key)
    
    def get_webhook_secret(self):
        return self.decrypt(self.webhook_secret)
    
    def __str__(self):
        return self.get_name_display()

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
        ('cancelled', 'Cancelado'),
        ('refunded', 'Reembolsado'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants_api.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Tenant al que pertenece este pago"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subscription = models.ForeignKey(UserSubscription, on_delete=models.SET_NULL, null=True, blank=True)
    provider = models.ForeignKey(PaymentProvider, on_delete=models.PROTECT)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # IDs externos del proveedor
    provider_payment_id = models.CharField(max_length=255, blank=True)
    provider_customer_id = models.CharField(max_length=255, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment {self.id} - {self.user.email} - {self.status}"

class WebhookEvent(models.Model):
    provider = models.ForeignKey(PaymentProvider, on_delete=models.CASCADE)
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    processed = models.BooleanField(default=False)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.provider.name} - {self.event_type} - {self.event_id}"