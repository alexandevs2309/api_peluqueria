from django.db import models
from django.conf import settings


class SettingsAuditLog(models.Model):
    """Log de auditoría para cambios en configuraciones críticas"""
    
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE, related_name='settings_audit_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='settings_changes')
    field_name = models.CharField(max_length=100)
    old_value = models.TextField()
    new_value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'created_at']),
            models.Index(fields=['field_name']),
        ]
    
    def __str__(self):
        return f"{self.tenant} - {self.field_name}: {self.old_value} → {self.new_value}"
