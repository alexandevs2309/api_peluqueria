from django.db import models
from django.conf import settings
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
    status = models.CharField(max_length=50, choices=[
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("canceled", "Canceled")
    ], default="pending")

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return f"Invoice #{self.id} - {self.user.email}"


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
