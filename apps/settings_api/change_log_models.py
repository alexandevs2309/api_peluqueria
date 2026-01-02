from django.db import models
from django.conf import settings
from django.utils import timezone

class SettingsChangeLog(models.Model):
    """Registro de cambios en configuraciones críticas"""
    
    SETTING_TYPES = [
        ('critical', 'Crítico'),
        ('sensitive', 'Sensible'),
        ('cosmetic', 'Cosmético')
    ]
    
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE, related_name='settings_changes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    setting_name = models.CharField(max_length=100)
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPES)
    
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField()
    
    confirmed = models.BooleanField(default=False)  # Si requirió confirmación
    impact_acknowledged = models.BooleanField(default=False)  # Si se reconoció el impacto
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'setting_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.tenant} - {self.setting_name}: {self.old_value} → {self.new_value}"