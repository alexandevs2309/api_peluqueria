from django.db import models
from django.conf import settings
from datetime import timedelta
from django.db.models import JSONField
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError


class SubscriptionPlan(models.Model):

    PLAN_CHOICES = [
        ('basic', 'Professional'),
        ('standard', 'Business'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    ]

    name = models.CharField(max_length=100, unique=True, choices=PLAN_CHOICES, help_text="Name of the subscription plan")
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_month = models.PositiveIntegerField(default=1, help_text="Duration in month for the subscription plan")
    stripe_price_id = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        db_index=True,
        help_text="Stripe Price ID (ej: price_...) para cobro recurrente"
    )
    is_active = models.BooleanField(default=True)
    max_employees = models.PositiveIntegerField(default=0)
    max_users = models.PositiveIntegerField(default=0)
    allows_multiple_branches = models.BooleanField(default=False, help_text="Permite multiples sucursales")
    features = JSONField(default=dict)
    commercial_benefits = JSONField(default=list, blank=True)

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

    def change_plan(self, new_plan):
        old_plan = self.plan

        if new_plan.max_employees < old_plan.max_employees:
            self._validate_employee_limit(new_plan)

        if not new_plan.allows_multiple_branches and old_plan.allows_multiple_branches:
            self._validate_branch_limit(new_plan)

        self.plan = new_plan
        self.save()

        SubscriptionAuditLog.objects.create(
            user=self.user,
            subscription=self,
            action='plan_changed',
            description=f'Plan cambiado de {old_plan.name} a {new_plan.name}'
        )

    def _validate_employee_limit(self, new_plan):
        from apps.employees_api.models import Employee

        tenant = self.user.tenant
        if not tenant:
            return

        current_employees = Employee.objects.filter(tenant=tenant, is_active=True).count()

        if current_employees > new_plan.max_employees:
            raise ValidationError(
                f'No puede cambiar a este plan. Tiene {current_employees} empleados activos, '
                f'pero el plan {new_plan.get_name_display()} permite maximo {new_plan.max_employees}. '
                f'Desactive empleados antes de cambiar de plan.'
            )

    def _validate_branch_limit(self, new_plan):
        from apps.settings_api.models import Branch

        tenant = self.user.tenant
        if not tenant:
            return

        branch_count = Branch.objects.filter(tenant=tenant, is_active=True).count()

        if branch_count > 1:
            raise ValidationError(
                f'No puede cambiar a este plan. Tiene {branch_count} sucursales activas, '
                f'pero el plan {new_plan.get_name_display()} solo permite 1 sucursal. '
                f'Desactive sucursales antes de cambiar de plan.'
            )

    def save(self, *args, **kwargs):
        if not self._state.adding:
            old = UserSubscription.objects.get(pk=self.pk)
            if old.is_active is False and self.is_active is True:
                raise ValueError("No se puede reactivar una suscripcion inactiva")

        if self._state.adding and not self.end_date:
            self.start_date = timezone.now()
            self.end_date = self.start_date + relativedelta(months=self.plan.duration_month)

        if self.end_date and self.end_date < timezone.now():
            self.is_active = False

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} -> {self.plan.name}"


class Subscription(models.Model):
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    stripe_subscription_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tenant', 'plan')

    def change_plan(self, new_plan):
        old_plan = self.plan

        if new_plan.max_employees < old_plan.max_employees:
            self._validate_employee_limit(new_plan)

        if not new_plan.allows_multiple_branches and old_plan.allows_multiple_branches:
            self._validate_branch_limit(new_plan)

        self.plan = new_plan
        self.save()

    def _validate_employee_limit(self, new_plan):
        from apps.employees_api.models import Employee

        current_employees = Employee.objects.filter(tenant=self.tenant, is_active=True).count()

        if current_employees > new_plan.max_employees:
            raise ValidationError(
                f'No puede cambiar a este plan. Tiene {current_employees} empleados activos, '
                f'pero el plan {new_plan.get_name_display()} permite maximo {new_plan.max_employees}. '
                f'Desactive empleados antes de cambiar de plan.'
            )

    def _validate_branch_limit(self, new_plan):
        from apps.settings_api.models import Branch

        branch_count = Branch.objects.filter(tenant=self.tenant, is_active=True).count()

        if branch_count > 1:
            raise ValidationError(
                f'No puede cambiar a este plan. Tiene {branch_count} sucursales activas, '
                f'pero el plan {new_plan.get_name_display()} solo permite 1 sucursal. '
                f'Desactive sucursales antes de cambiar de plan.'
            )

    def __str__(self):
        return f"{self.tenant.name} - {self.plan.name} - {self.stripe_subscription_id}"


class SubscriptionAuditLog(models.Model):
    ACTION_CHOICES = [
        ('created', 'Creacion'),
        ('updated', 'Actualizacion'),
        ('deleted', 'Eliminacion'),
        ('renewed', 'Renovacion'),
        ('cancelled', 'Cancelacion'),
        ('expired', 'Expiracion'),
        ('payment_failed', 'Fallo de pago'),
        ('payment_successful', 'Pago exitoso'),
        ('plan_changed', 'Cambio de plan'),
        ('trial_started', 'Inicio de prueba'),
        ('trial_ended', 'Fin de prueba'),
        ('subscription_suspended', 'Suspension de suscripcion'),
        ('subscription_resumed', 'Reanudacion de suscripcion'),
        ('subscription_paused', 'Pausa de suscripcion'),
        ('subscription_reactivated', 'Reactivacion de suscripcion'),
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
