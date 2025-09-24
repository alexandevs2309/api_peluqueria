from django.db import models
from django.conf import settings
from django.utils import timezone

class Tenant(models.Model):
    PLAN_CHOICES = [
        ("free", "Free"),
        ("basic", "Basic"),
        ("premium", "Premium"),
    ]
    SUBSCRIPTION_STATUS = [
        ("trial", "Trial"),
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("cancelled", "Cancelled"),
    ]

    name = models.CharField(max_length=100)
    subdomain = models.CharField(max_length=50, unique=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_tenants")

    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES, default="free")
    subscription_plan = models.ForeignKey('subscriptions_api.SubscriptionPlan', on_delete=models.PROTECT, null=True, blank=True)
    subscription_status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS, default="trial")
    trial_end_date = models.DateField(null=True, blank=True)
    billing_info = models.JSONField(default=dict, blank=True)
    settings = models.JSONField(default=dict, blank=True)

    max_employees = models.PositiveIntegerField(default=5)
    max_users = models.PositiveIntegerField(default=10)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Sincronizar plan_type con subscription_plan si existe
        if self.subscription_plan:
            # Si hay un subscription_plan, usar su tipo
            self.plan_type = self.subscription_plan.plan_type
        elif not self.subscription_plan and self.plan_type == 'free':
            # Si no hay subscription_plan y plan_type es free, mantenerlo
            pass
        else:
            # Si no hay subscription_plan, establecer como free por defecto
            self.plan_type = 'free'

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.subdomain})"
