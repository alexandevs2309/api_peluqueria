"""
Audit Trail profesional para trazabilidad de negocio
apps/audit_api/models.py - EXTENDER EXISTENTE
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import json


class AuditAction(models.TextChoices):
    CREATE = 'create', 'Create'
    UPDATE = 'update', 'Update'
    SOFT_DELETE = 'soft_delete', 'Soft Delete'
    RESTORE = 'restore', 'Restore'
    HARD_DELETE = 'hard_delete', 'Hard Delete'
    LOGIN = 'login', 'Login'
    LOGOUT = 'logout', 'Logout'


class BusinessAuditLog(models.Model):
    """
    Auditoría de acciones de negocio críticas.
    Separada de logs técnicos (structlog).
    """
    # Contexto
    tenant_id = models.IntegerField(db_index=True)
    actor = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_actions'
    )
    
    # Acción
    action = models.CharField(max_length=20, choices=AuditAction.choices)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Objeto afectado
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Cambios
    changes = models.JSONField(default=dict, blank=True)
    previous_values = models.JSONField(default=dict, blank=True)
    
    # Metadatos
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        db_table = 'business_audit_log'
        indexes = [
            models.Index(fields=['tenant_id', 'timestamp']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['actor', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.actor} {self.action} {self.content_object} at {self.timestamp}"


class AuditService:
    """Servicio para registrar auditoría de forma controlada."""
    
    @staticmethod
    def log_action(
        tenant_id: int,
        actor,
        action: str,
        content_object,
        changes: dict = None,
        previous_values: dict = None,
        request=None
    ):
        """Registra acción de auditoría."""
        audit_data = {
            'tenant_id': tenant_id,
            'actor': actor,
            'action': action,
            'content_object': content_object,
            'changes': changes or {},
            'previous_values': previous_values or {},
        }
        
        if request:
            audit_data.update({
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
            })
        
        return BusinessAuditLog.objects.create(**audit_data)
    
    @staticmethod
    def log_soft_delete(tenant_id: int, actor, instance, request=None):
        """Registra soft delete específicamente."""
        return AuditService.log_action(
            tenant_id=tenant_id,
            actor=actor,
            action=AuditAction.SOFT_DELETE,
            content_object=instance,
            request=request
        )