from django.db import models
from django.conf import settings
from datetime import timedelta
from django.db.models import JSONField
from django.utils import timezone
from dateutil.relativedelta import relativedelta

class SubscriptionPlan(models.Model):

    PLAN_CHOICES = [
        ('basic', 'Plan Básico'),
        ('standard', 'Plan Estándar'),
        ('premium', 'Plan Premium'),
        ('enterprise', 'Plan Empresarial'),
    ]

    name = models.CharField(max_length=100, unique=True , choices=PLAN_CHOICES, help_text="Name of the subscription plan")
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_month = models.PositiveIntegerField( default = 1,help_text="Duration in month for the subscription plan")
    is_active = models.BooleanField(default=True)
    max_employees = models.PositiveIntegerField(default=0)
    max_users = models.PositiveIntegerField(default=0)
    features = JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_name_display()
    
class UserSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='user_subscriptions')
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Handle reactivation prevention
        if not self._state.adding:
            old = UserSubscription.objects.get(pk=self.pk)
            if old.is_active is False and self.is_active is True:
                raise ValueError("No se puede reactivar una suscripción inactiva")
        
        # Handle automatic date calculation for new subscriptions
        if self._state.adding and not self.end_date:
            self.start_date = timezone.now()
            self.end_date = self.start_date + relativedelta(months=self.plan.duration_month)
        
        # Handle expired subscriptions
        if self.end_date and self.end_date < timezone.now():
            self.is_active = False
            
        # Single save operation
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} -> {self.plan.name}"

class Subscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"

class SubscriptionAuditLog(models.Model):
    ACTION_CHOICES = [
        ('created', 'Creación'),
        ('updated', 'Actualización'),
        ('deleted', 'Eliminación'),
        ('renewed', 'Renovación'),
        ('cancelled', 'Cancelación'),
        ('expired', 'Expiración'),
        ('payment_failed', 'Fallo de pago'),
        ('payment_successful', 'Pago exitoso'),
        ('plan_changed', 'Cambio de plan'),
        ('trial_started', 'Inicio de prueba'),
        ('trial_ended', 'Fin de prueba'),
        ('subscription_suspended', 'Suspensión de suscripción'),
        ('subscription_resumed', 'Reanudación de suscripción'),
        ('subscription_paused', 'Pausa de suscripción'),
        ('subscription_reactivated', 'Reactivación de suscripción'),
    ]


    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription_audit_logs')
    subscription = models.ForeignKey('UserSubscription', on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, help_text="Action performed on the subscription")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Subscription Audit Log'
        verbose_name_plural = 'Subscription Audit Logs'

    def __str__(self):
        return f"{self.user.email} - {self.action} at {self.created_at}"
