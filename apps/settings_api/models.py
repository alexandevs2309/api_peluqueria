from django.db import models
from django.conf import settings as django_settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

class Branch(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Setting(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=False, blank=False, verbose_name=_("Sucursal"))
    business_name = models.CharField(_("Nombre del negocio"), max_length=255 , blank=False, null=False)
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
    theme = models.CharField(_("Tema visual"), max_length=50, default="light")  # light / dark / custom
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["branch"], name="unique_setting_per_branch")
        ]


    def save(self, *args, **kwargs):
        if not self.pk and Setting.objects.filter(branch=self.branch).exists():
            raise ValueError(_("Solo puede existir un Setting por sucursal"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.business_name} ({self.branch or 'General'})"

class SettingAuditLog(models.Model):
    setting = models.ForeignKey(Setting, on_delete=models.CASCADE)
    changed_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    change_summary = models.JSONField()

    def __str__(self):
        return f"Cambio en {self.setting} por {self.changed_by} el {self.changed_at}"
