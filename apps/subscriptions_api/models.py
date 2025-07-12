from django.db import models
from django.conf import settings
from datetime import timedelta
from django.utils import timezone
from dateutil.relativedelta import relativedelta

class SubscriptionPlan(models.Model):

    PLAN_CHOICES = [
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    ]

    name = models.CharField(max_length=100, unique=True , choices=PLAN_CHOICES, help_text="Name of the subscription plan")
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_month = models.PositiveIntegerField( default = 1,help_text="Duration in month for the subscription plan")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class UserSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='user_subscriptions')
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.start_date = timezone.now()
            self.end_date = self.start_date + relativedelta(months=self.plan.duration_month)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} -> {self.plan.name}"