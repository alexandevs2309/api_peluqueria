from django.db import models

class BarbershopSettings(models.Model):
    tenant = models.OneToOneField('tenants_api.Tenant', on_delete=models.CASCADE, related_name='barbershop_settings')
    name = models.CharField(max_length=200, blank=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#2563EB', help_text='Color primario (hex)')
    secondary_color = models.CharField(max_length=7, default='#4F46E5', help_text='Color secundario (hex)')
    accent_color = models.CharField(max_length=7, default='#059669', help_text='Color de acento (hex)')
    currency = models.CharField(max_length=3, default='COP')
    currency_symbol = models.CharField(max_length=5, default='$')
    business_hours = models.JSONField(default=dict, blank=True)
    contact = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Barbershop Settings'
        verbose_name_plural = 'Barbershop Settings'

    def __str__(self):
        return f"Settings for {self.tenant.name}"