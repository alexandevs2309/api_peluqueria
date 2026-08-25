from django.db import models
from django.conf import settings as django_settings


def _encrypt_value(value):
    """Encriptar valor sensible con Fernet."""
    if not value:
        return value
    try:
        from cryptography.fernet import Fernet
        key = getattr(django_settings, 'FERNET_KEY', None)
        if not key:
            return value
        if isinstance(key, str):
            key = key.encode()
        f = Fernet(key)
        if isinstance(value, str):
            value = value.encode()
        return f.encrypt(value).decode()
    except Exception:
        return value


def _decrypt_value(value):
    """Desencriptar valor sensible con Fernet."""
    if not value:
        return value
    try:
        from cryptography.fernet import Fernet
        key = getattr(django_settings, 'FERNET_KEY', None)
        if not key:
            return value
        if isinstance(key, str):
            key = key.encode()
        f = Fernet(key)
        return f.decrypt(value.encode()).decode()
    except Exception:
        return value


class BarbershopSettings(models.Model):
    tenant = models.OneToOneField('tenants_api.Tenant', on_delete=models.CASCADE, related_name='barbershop_settings')
    name = models.CharField(max_length=200, blank=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#2563EB', help_text='Color primario (hex)')
    secondary_color = models.CharField(max_length=7, default='#4F46E5', help_text='Color secundario (hex)')
    accent_color = models.CharField(max_length=7, default='#059669', help_text='Color de acento (hex)')
    currency = models.CharField(max_length=3, default='USD')
    currency_symbol = models.CharField(max_length=5, default='$')
    business_hours = models.JSONField(default=dict, blank=True)
    contact = models.JSONField(default=dict, blank=True)

    # WhatsApp QR Settings
    whatsapp_enabled = models.BooleanField(default=False)
    whatsapp_instance_name = models.CharField(max_length=100, blank=True)
    whatsapp_token = models.CharField(max_length=255, blank=True)
    whatsapp_webhook_secret = models.CharField(max_length=255, blank=True, help_text="Secret for Evolution API webhook signature verification")
    whatsapp_status = models.CharField(
        max_length=50,
        choices=[
            ('disconnected', 'Desconectado'),
            ('connecting', 'Conectando'),
            ('connected', 'Conectado')
        ],
        default='disconnected'
    )
    whatsapp_phone = models.CharField(max_length=32, blank=True)

    # =============================================
    # PASARELA DE PAGO — Credenciales por Tenant
    # =============================================

    # Proveedor activo: 'cardnet', 'azul', 'stripe', 'paypal', 'manual'
    active_payment_provider = models.CharField(max_length=20, default='manual', blank=True)
    payment_sandbox = models.BooleanField(default=True, help_text='Modo sandbox/pruebas')

    # --- CardNET ---
    cardnet_merchant_id = models.CharField(max_length=100, blank=True)
    cardnet_terminal_id = models.CharField(max_length=100, blank=True)
    cardnet_api_key = models.CharField(max_length=500, blank=True)

    # --- Azul ---
    azul_merchant_id = models.CharField(max_length=100, blank=True)
    azul_store_id = models.CharField(max_length=100, blank=True)
    azul_auth1 = models.CharField(max_length=500, blank=True)
    azul_auth2 = models.CharField(max_length=500, blank=True)
    azul_cert_key = models.CharField(max_length=500, blank=True)

    # --- Stripe ---
    stripe_secret_key = models.CharField(max_length=500, blank=True)
    stripe_publishable_key = models.CharField(max_length=500, blank=True)
    stripe_webhook_secret = models.CharField(max_length=500, blank=True)

    # --- PayPal ---
    paypal_client_id = models.CharField(max_length=500, blank=True)
    paypal_client_secret = models.CharField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    _ENCRYPTED_FIELDS = [
        'cardnet_api_key', 'azul_auth1', 'azul_auth2', 'azul_cert_key',
        'stripe_secret_key', 'stripe_webhook_secret', 'paypal_client_secret',
    ]

    class Meta:
        verbose_name = 'Barbershop Settings'
        verbose_name_plural = 'Barbershop Settings'

    def __str__(self):
        return f"Settings for {self.tenant.name}"

    def save(self, *args, **kwargs):
        for field_name in self._ENCRYPTED_FIELDS:
            value = getattr(self, field_name, '')
            if value and not value.startswith('gAAAAA'):
                setattr(self, field_name, _encrypt_value(value))
        super().save(*args, **kwargs)

    def get_payment_credential(self, field_name):
        """Obtener credencial de pago desencriptada."""
        value = getattr(self, field_name, '')
        if value and value.startswith('gAAAAA'):
            return _decrypt_value(value)
        return value