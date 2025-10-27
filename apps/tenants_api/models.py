from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

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

    name = models.CharField(max_length=100, unique=True)
    subdomain = models.CharField(max_length=50, unique=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_tenants")
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=2, blank=True, null=True)  # ISO country code

    plan_type = models.CharField(max_length=20, choices=PLAN_CHOICES, default="free")
    subscription_plan = models.ForeignKey('subscriptions_api.SubscriptionPlan', on_delete=models.SET_NULL, null=True, blank=True)
    subscription_status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS, default="trial")
    trial_end_date = models.DateField(null=True, blank=True)
    trial_notifications_sent = models.JSONField(default=dict, blank=True)
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
            
            # TODOS los planes empiezan con trial (solo en creación)
            if not self.pk:
                self.subscription_status = 'trial'
                
                if plan.name == 'enterprise':
                    trial_days = 14
                else:  # basic, standard, premium
                    trial_days = 7
                    
                self.trial_end_date = timezone.now().date() + timedelta(days=trial_days)
            
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
    
    def has_feature(self, feature_name):
        """Check if tenant has access to specific feature"""
        if not self.subscription_plan:
            return False
        features = self.subscription_plan.features or {}
        return features.get(feature_name, False)
    
    def can_add_user(self):
        """Check if tenant can add more users"""
        if self.max_users == 0:  # Unlimited
            return True
        current_users = self.users.filter(is_active=True).count()
        return current_users < self.max_users
    
    def can_add_employee(self):
        """Check if tenant can add more employees"""
        if self.max_employees == 0:  # Unlimited
            return True
        current_employees = self.users.filter(
            is_active=True, 
            role='ClientStaff'
        ).count()
        return current_employees < self.max_employees
    
    def get_user_usage(self):
        """Get current user usage stats"""
        current_users = self.users.filter(is_active=True).count()
        return {
            'current': current_users,
            'limit': self.max_users,
            'unlimited': self.max_users == 0,
            'percentage': (current_users / self.max_users * 100) if self.max_users > 0 else 0
        }
    
    def get_employee_usage(self):
        """Get current employee usage stats"""
        current_employees = self.users.filter(
            is_active=True, 
            role='ClientStaff'
        ).count()
        return {
            'current': current_employees,
            'limit': self.max_employees,
            'unlimited': self.max_employees == 0,
            'percentage': (current_employees / self.max_employees * 100) if self.max_employees > 0 else 0
        }

    def is_trial_expired(self):
        """Verificar si el trial ha expirado"""
        return (self.subscription_status == 'trial' and 
                self.trial_end_date and 
                timezone.now().date() > self.trial_end_date)
    
    def get_trial_days_remaining(self):
        """Obtener días restantes del trial"""
        if self.subscription_status != 'trial' or not self.trial_end_date:
            return 0
        days_left = (self.trial_end_date - timezone.now().date()).days
        return max(0, days_left)
    
    def check_and_suspend_expired_trial(self):
        """Verificar y suspender trial expirado"""
        if self.is_trial_expired():
            self.subscription_status = 'suspended'
            self.save()
            return True
        return False
    
    def get_access_level(self):
        """Determinar nivel de acceso del tenant"""
        if self.subscription_status == 'active':
            return 'full'
        elif self.subscription_status == 'trial':
            return 'full' if not self.is_trial_expired() else 'grace'
        elif self.subscription_status == 'suspended':
            if self.trial_end_date:
                days_since_expiry = (timezone.now().date() - self.trial_end_date).days
                return 'grace' if days_since_expiry <= 3 else 'blocked'
            return 'blocked'
        return 'blocked'
    
    def should_send_trial_notification(self, days_before):
        """Verificar si debe enviar notificación de trial"""
        days_left = self.get_trial_days_remaining()
        notification_key = f'trial_warning_{days_before}d'
        
        return (days_left == days_before and 
                not self.trial_notifications_sent.get(notification_key, False))
    
    def mark_notification_sent(self, days_before):
        """Marcar notificación como enviada"""
        notification_key = f'trial_warning_{days_before}d'
        self.trial_notifications_sent[notification_key] = True
        self.save(update_fields=['trial_notifications_sent'])
    
    def activate_subscription(self):
        """Activar suscripción (después de pago)"""
        self.subscription_status = 'active'
        self.trial_end_date = None
        self.trial_notifications_sent = {}
        self.save()

    def __str__(self):
        return f"{self.name} ({self.subdomain})"
