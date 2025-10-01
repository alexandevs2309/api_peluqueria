from django.db import models
from django.conf import settings
from django.utils import timezone

class Tenant(models.Model):
    PLAN_CHOICES = [
        ("free", "Free"),
        ("basic", "Basic"),
        ("premium", "Premium"),
        ("enterprise", "Enterprise"),
        ("standard", "Standard"),
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
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES, default="free")
    subscription_plan = models.ForeignKey('subscriptions_api.SubscriptionPlan', on_delete=models.SET_NULL, null=True, blank=True)
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
        # Heredar TODAS las características del plan seleccionado
        if self.subscription_plan:
            plan = self.subscription_plan
            
            # Características básicas
            self.plan_type = plan.name
            self.max_employees = plan.max_employees
            self.max_users = plan.max_users
            
            # Lógica específica por tipo de plan
            if plan.name == 'free':
                # Plan Free: 7 días de prueba (duration_month = 0 significa días)
                self.subscription_status = 'trial'
                # Para plan free, usar 7 días independientemente del duration_month
                self.trial_end_date = timezone.now().date() + timezone.timedelta(days=7)
            elif plan.name == 'basic':
                # Plan Basic: Suscripción mensual activa
                self.subscription_status = 'active'
                self.trial_end_date = None
            elif plan.name == 'premium':
                # Plan Premium: Suscripción mensual activa con características premium
                self.subscription_status = 'active'
                self.trial_end_date = None
            elif plan.name == 'enterprise':
                # Plan Enterprise: Suscripción anual activa, sin límites
                self.subscription_status = 'active'
                self.trial_end_date = None
            elif plan.name == 'standard':
                # Plan Standard: Suscripción mensual activa
                self.subscription_status = 'active'
                self.trial_end_date = None
            
            # Heredar todas las características del plan
            self.settings.update({
                'plan_features': plan.features,
                'plan_price': str(plan.price),
                'plan_duration_months': plan.duration_month,
                'plan_description': plan.description,
                'plan_type_logic': f'Plan {plan.name} configurado automáticamente',
                'inherited_at': str(timezone.now())
            })
                
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.subdomain})"
