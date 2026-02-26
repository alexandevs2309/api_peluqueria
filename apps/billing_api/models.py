from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.subscriptions_api.models import UserSubscription


class Invoice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invoices")
    subscription = models.ForeignKey(UserSubscription, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    issued_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    description = models.TextField(blank=True)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=100, blank=True)  # Ej: "manual", "stripe", "paypal"
    stripe_payment_intent_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,  # ✅ Permitir NULL para facturas manuales
        unique=True,  # ✅ Prevenir duplicados
        db_index=True
    )  # Para reconciliación
    status = models.CharField(max_length=50, choices=[
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("canceled", "Canceled")
    ], default="pending")

    class Meta:
        ordering = ["-issued_at"]
        indexes = [
            models.Index(fields=['user', 'issued_at']),
            models.Index(fields=['status']),
            models.Index(fields=['is_paid']),
            models.Index(fields=['issued_at']),
            models.Index(fields=['stripe_payment_intent_id']),
        ]

    def __str__(self):
        return f"Invoice #{self.id} - {self.user.email}"
    
    def save(self, *args, **kwargs):
        if self.pk:
            original = Invoice.objects.get(pk=self.pk)
            if original.amount != self.amount:
                raise ValidationError("No se puede modificar el monto de una factura ya creada.")
            if original.user_id != self.user_id:
                raise ValidationError("No se puede cambiar el usuario de la factura.")
            if original.subscription_id != self.subscription_id:
                raise ValidationError("No se puede cambiar la suscripción asociada.")
        super().save(*args, **kwargs)


class PaymentAttempt(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="attempts")
    attempted_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=[
        ("success", "Success"),
        ("failed", "Failed")
    ])
    message = models.TextField(blank=True)

    def __str__(self):
        return f"Attempt for Invoice #{self.invoice.id} - {self.status}"
