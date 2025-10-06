import sys
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from .utils import create_audit_log
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save)
def audit_log_on_save(sender, instance, created, **kwargs):
    """Registra automáticamente todas las operaciones de guardado de modelos"""
    # 🚫 Evitar ejecución durante migraciones o comandos especiales
    if any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'collectstatic', 'test', 'flush']):
        return

    # Saltar modelos del sistema y el propio modelo de auditoría
    if sender._meta.app_label in ['auth', 'admin', 'contenttypes', 'sessions', 'audit_api']:
        return
    
    action = 'CREATE' if created else 'UPDATE'
    
    # Obtener cambios para operaciones de actualización
    changes = {}
    if not created and hasattr(instance, '_original_state'):
        changes = {
            field.name: str(getattr(instance, field.name))
            for field in instance._meta.fields
            if str(getattr(instance, field.name)) != str(instance._original_state.get(field.name, ''))
        }
    
    # Determinar el usuario
    user = None
    if hasattr(instance, 'created_by') and instance.created_by:
        user = instance.created_by
    elif hasattr(instance, 'user') and instance.user:
        user = instance.user
    
    create_audit_log(
        user=user,
        action=action,
        description=f"{sender._meta.verbose_name} {action.lower()}d",
        content_object=instance,
        extra_data={'changes': changes}
    )


@receiver(post_delete)
def audit_log_on_delete(sender, instance, **kwargs):
    """Registra automáticamente todas las operaciones de eliminación de modelos"""
    # 🚫 Evitar ejecución durante migraciones o comandos especiales
    if any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'collectstatic', 'test', 'flush']):
        return

    if sender._meta.app_label in ['auth', 'admin', 'contenttypes', 'sessions', 'audit_api']:
        return
    
    user = None
    if hasattr(instance, 'created_by') and instance.created_by:
        user = instance.created_by
    
    create_audit_log(
        user=user,
        action='DELETE',
        description=f"{sender._meta.verbose_name} eliminado",
        content_object=None,
        extra_data={'deleted_object': str(instance)}
    )
