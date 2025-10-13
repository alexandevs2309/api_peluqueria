from django.db import models
from django.conf import settings as django_settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

class Branch(models.Model):
    """Sucursales - Solo para planes Enterprise/Multi-Branch"""
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    is_main = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'name'], name='unique_branch_per_tenant')
        ]

    def save(self, *args, **kwargs):
        # Verificar que el tenant tenga un plan que permita múltiples sucursales
        subscription = self.tenant.subscription_set.filter(is_active=True).first()
        if subscription and not subscription.plan.allows_multiple_branches:
            if Branch.objects.filter(tenant=self.tenant).exists() and not self.pk:
                raise ValueError(_("Su plan actual no permite múltiples sucursales"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"

class Setting(models.Model):
    """Configuraciones por sucursal - Solo para planes Enterprise"""
    branch = models.OneToOneField(Branch, on_delete=models.CASCADE, related_name='settings')
    business_name = models.CharField(_("Nombre del negocio"), max_length=255)
    business_email = models.EmailField(_("Email de contacto"), blank=True, null=True)
    phone_number = models.CharField(_("Teléfono"), max_length=50, blank=True, null=True)
    address = models.TextField(_("Dirección"), blank=True, null=True)
    currency = models.CharField(_("Moneda"), max_length=10, default="USD")
    tax_percentage = models.DecimalField(
        _("Porcentaje de impuestos"),
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    timezone = models.CharField(_("Zona horaria"), max_length=100, default="America/Santo_Domingo")
    business_hours = models.JSONField(_("Horario de atención"), default=dict, blank=True)
    preferences = models.JSONField(_("Preferencias generales"), default=dict, blank=True)
    logo = models.ImageField(_("Logo del negocio"), upload_to="settings/logo/", blank=True, null=True)
    theme = models.CharField(_("Tema visual"), max_length=50, default="light")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business_name} - {self.branch.name}"

class SystemSettings(models.Model):
    """Configuraciones globales del sistema SaaS"""
    # Configuración General
    platform_name = models.CharField(_("Nombre de la plataforma"), max_length=255, default="BarberSaaS")
    support_email = models.EmailField(_("Email de soporte"), default="soporte@barbersaas.com")
    
    # Configuración de Clientes
    max_tenants = models.PositiveIntegerField(_("Máximo de clientes"), default=100)
    trial_days = models.PositiveIntegerField(
        _("Días de prueba"), 
        default=7,
        validators=[MinValueValidator(0), MaxValueValidator(365)]
    )
    default_currency = models.CharField(_("Moneda por defecto"), max_length=10, default="USD")
    
    # Configuración de Plataforma
    platform_domain = models.CharField(_("Dominio principal"), max_length=255, blank=True)
    supported_languages = models.JSONField(_("Idiomas habilitados"), default=list)
    platform_commission_rate = models.DecimalField(
        _("Comisión de plataforma (%)"),
        max_digits=5,
        decimal_places=2,
        default=5.00,
        validators=[MinValueValidator(0), MaxValueValidator(50)]
    )
    
    # Límites por Plan
    basic_plan_max_employees = models.PositiveIntegerField(_("Plan básico - máx. empleados"), default=5)
    premium_plan_max_employees = models.PositiveIntegerField(_("Plan premium - máx. empleados"), default=25)
    enterprise_plan_max_employees = models.PositiveIntegerField(_("Plan enterprise - máx. empleados"), default=999)
    
    # Integraciones Globales
    stripe_enabled = models.BooleanField(_("Stripe habilitado"), default=True)
    paypal_enabled = models.BooleanField(_("PayPal habilitado"), default=False)
    twilio_enabled = models.BooleanField(_("SMS (Twilio) habilitado"), default=False)
    sendgrid_enabled = models.BooleanField(_("Email (SendGrid) habilitado"), default=True)
    aws_s3_enabled = models.BooleanField(_("Almacenamiento (AWS S3) habilitado"), default=True)
    
    # Preferencias del Sistema
    maintenance_mode = models.BooleanField(_("Modo mantenimiento"), default=False)
    email_notifications = models.BooleanField(_("Notificaciones por email"), default=True)
    auto_suspend_expired = models.BooleanField(_("Suspender automáticamente vencidos"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Configuración del Sistema")
        verbose_name_plural = _("Configuraciones del Sistema")

    def save(self, *args, **kwargs):
        # Solo permitir una instancia de configuraciones del sistema
        if not self.pk and SystemSettings.objects.exists():
            raise ValueError(_("Solo puede existir una configuración del sistema"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Configuraciones del Sistema - {self.platform_name}"

    @classmethod
    def get_settings(cls):
        """Obtener o crear la configuración del sistema"""
        settings, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'platform_name': 'BarberSaaS',
                'support_email': 'soporte@barbersaas.com',
                'max_tenants': 100,
                'trial_days': 7,
                'default_currency': 'USD',
                'platform_domain': '',
                'supported_languages': ['es', 'en'],
                'platform_commission_rate': 5.00,
                'basic_plan_max_employees': 5,
                'premium_plan_max_employees': 25,
                'enterprise_plan_max_employees': 999,
                'stripe_enabled': True,
                'paypal_enabled': False,
                'twilio_enabled': False,
                'sendgrid_enabled': True,
                'aws_s3_enabled': True,
                'maintenance_mode': False,
                'email_notifications': True,
                'auto_suspend_expired': True
            }
        )
        return settings
