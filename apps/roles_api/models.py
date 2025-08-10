from django.conf import settings
from django.db import models
from django.contrib.auth.models import Permission
from django.utils.timezone import now



class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, blank=True, related_name='roles')

    class Meta:
        indexes = [
            models.Index(fields=['name'], name='role_name_idx'),
        ]

    def __str__(self):
        return self.name


class UserRole(models.Model):
    user = models.ForeignKey(
            settings.AUTH_USER_MODEL, # <-- CAMBIO AQUÍ
            on_delete=models.CASCADE,
            related_name='user_roles'
        )   
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'role')
        indexes = [
            models.Index(fields=['user', 'role']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.role.name}"

class AdminActionLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, # <-- CAMBIO AQUÍ
        on_delete=models.CASCADE,
        related_name='admin_logs'
    )
    action = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(default=now)

    class Meta:
        indexes = [
            models.Index(fields=['timestamp'], name='admin_action_timestamp_idx'),
        ]
    def __str__(self):
        return f"{self.user.email} - {self.action} @ {self.timestamp}"
    

