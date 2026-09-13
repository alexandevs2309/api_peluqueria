from django.db import models
from django.conf import settings
from django.core import signing
from django.db.models import Q
from apps.subscriptions_api.models import UserSubscription
from apps.payments_api.storage import PaymentProofStorage
import uuid

class EncryptedFieldMixin:
    """
    Mixin que 'encripta' campos usando django.core.signing (HMAC + compresion).

    ADVERTENCIA TECNICA: django.core.signing NO es cifrado simetrico real.
    Proporciona integridad (HMAC-SHA256) pero no confidencialidad verdadera:
    el valor base64 es reversible si se tiene la SECRET_KEY.
    Para cifrado real usar django-encrypted-model-fields o cryptography.Fernet.
    Pendiente migrar antes de almacenar claves de produccion de terceros.
    """

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

    @staticmethod
    def _is_signed(value):
        """Check if a value appears to be a signed string.
        Uses structural validation to avoid double signing after key rotation.
        """
        # Structural validation: signed strings contain exactly two ':' separators
        if value.count(":") == 2:
            return True
        try:
            signing.loads(value, salt="payment_provider")
            return True
        except (signing.BadSignature, signing.SignatureExpired):
            return False

class PaymentProvider(models.Model, EncryptedFieldMixin):
    PROVIDER_CHOICES = [
        ('azul', 'Azul (RD)'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('cardnet', 'CardNET (RD)'),
        ('manual', 'Manual'),
    ]
    
    name = models.CharField(max_length=50, choices=PROVIDER_CHOICES, unique=True)
    is_active = models.BooleanField(default=True)
    api_key = models.CharField(max_length=512, blank=True, editable=False,
                                help_text="Encriptado automaticamente. No modificar manualmente.")
    webhook_secret = models.CharField(max_length=512, blank=True, editable=False,
                                      help_text="Encriptado automaticamente. No modificar manualmente.")
    
    def save(self, *args, **kwargs):
        if self.api_key and not self._is_signed(self.api_key):
            self.api_key = self.encrypt(self.api_key)
        if self.webhook_secret and not self._is_signed(self.webhook_secret):
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
        help_text="Tenant al que pertenece este pago",
        db_index=True,
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    subscription = models.ForeignKey(UserSubscription, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    provider = models.ForeignKey(PaymentProvider, on_delete=models.PROTECT, db_index=True)
    
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


class PaymentProof(models.Model):
    """Comprobante de pago manual (transferencia/depósito) presentado por el
    cliente y revisado por un administrador.

    Reglas de negocio:
      - Un pago puede tener a lo sumo UN comprobante 'pending' a la vez
        (restricción UniqueConstraint condicional): evita colas de revisiones
        y obliga a resolver cada comprobante antes de presentar otro.
      - Un pago nunca puede tener más de un comprobante 'approved'
        (UniqueConstraint condicional): garantiza que la aprobación es única.
      - Tras un rechazo el cliente puede volver a presentar un comprobante
        para el mismo Payment (folio de transferencia distinto o corregido).
      - El archivo se guarda FUERA de MEDIA_ROOT (PaymentProofStorage) y se
        sirve solo vía el endpoint protegido manual_proof_download.
    """

    DECISION_CHOICES = [
        ('pending', 'Pendiente de revisión'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        'Payment',
        on_delete=models.CASCADE,
        related_name='proofs',
        db_index=True,
        help_text="Pago manual al que corresponde este comprobante"
    )
    file = models.FileField(
        storage=PaymentProofStorage(),
        upload_to='proofs',
        help_text="Archivo del comprobante (PDF, JPG, PNG o WebP)"
    )
    file_name = models.CharField(
        max_length=255, blank=True,
        help_text="Nombre de archivo original saneado (sin ruta)"
    )
    bank_reference = models.CharField(
        max_length=255, db_index=True,
        help_text="Referencia bancaria normalizada de la transferencia/depósito"
    )
    amount_provided = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Importe declarado por el cliente en el comprobante"
    )
    decision = models.CharField(
        max_length=20,
        choices=DECISION_CHOICES,
        default='pending',
        db_index=True,
        help_text="Decisión administrativa sobre este comprobante"
    )
    decision_note = models.TextField(
        blank=True,
        help_text="Motivo/nota del administrador (obligatorio en el rechazo)"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_payment_proofs',
        help_text="Administrador que revisó este comprobante"
    )
    reviewed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Fecha/hora de la revisión (aprobación o rechazo)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Comprobante de pago manual'
        verbose_name_plural = 'Comprobantes de pago manual'
        constraints = [
            models.UniqueConstraint(
                fields=['payment'],
                condition=Q(decision='pending'),
                name='one_pending_proof_per_payment'
            ),
            models.UniqueConstraint(
                fields=['payment'],
                condition=Q(decision='approved'),
                name='one_approved_proof_per_payment'
            ),
        ]

    def __str__(self):
        return f"PaymentProof {self.id} - Payment {self.payment_id} - {self.decision}"


class WebhookEvent(models.Model):
    provider = models.ForeignKey(PaymentProvider, on_delete=models.CASCADE, db_index=True)
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    processed = models.BooleanField(default=False)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.provider.name} - {self.event_type} - {self.event_id}"