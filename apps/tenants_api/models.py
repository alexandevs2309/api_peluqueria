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
    subscription_status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS, default="trial")
    trial_end_date = models.DateField(null=True, blank=True)
    billing_info = models.JSONField(default=dict, blank=True)
    settings = models.JSONField(default=dict, blank=True)

    max_employees = models.PositiveIntegerField(default=5)
    max_users = models.PositiveIntegerField(default=10)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.subdomain})"
