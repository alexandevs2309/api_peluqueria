"""
Base models para soft delete y auditoría
apps/utils/models.py
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    """Manager que excluye registros soft-deleted por defecto."""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def with_deleted(self):
        """Incluye registros soft-deleted explícitamente."""
        return super().get_queryset()
    
    def deleted_only(self):
        """Solo registros soft-deleted."""
        return super().get_queryset().filter(is_deleted=True)


class SoftDeleteModel(models.Model):
    """
    Base abstracto para modelos que requieren soft delete.
    
    USAR EN: payroll, pos, clients, employees, subscriptions
    NO USAR EN: logs, audit, tokens, settings, auth
    """
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_deleted'
    )
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Manager sin filtros
    
    class Meta:
        abstract = True
    
    def soft_delete(self, user=None):
        """Soft delete con auditoría."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
    
    def restore(self):
        """Restaurar registro soft-deleted."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])


class AuditableModel(models.Model):
    """
    Base para modelos que requieren timestamps de auditoría.
    Complementa SoftDeleteModel.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class BusinessModel(SoftDeleteModel, AuditableModel):
    """
    Combinación de soft delete + timestamps.
    Para modelos de dominio críticos.
    """
    class Meta:
        abstract = True