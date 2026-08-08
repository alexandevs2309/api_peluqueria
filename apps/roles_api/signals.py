import logging

from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from apps.roles_api.default_permissions import (
    ensure_role_default_permissions,
    sync_all_default_role_permissions,
)
from apps.roles_api.models import Role


logger = logging.getLogger(__name__)


@receiver(post_save, sender=Role, dispatch_uid='roles_api_sync_role_on_save')
def sync_role_permissions_on_save(sender, instance, **kwargs):
    """Sincroniza permisos cada vez que se guarda un Role (desde admin o código)."""
    try:
        count = ensure_role_default_permissions(instance)
        if count:
            logger.info("Role '%s' synced: %s permissions", instance.name, count)
    except Exception:
        logger.exception("Failed to sync permissions for role '%s'", instance.name)


@receiver(post_migrate, dispatch_uid='roles_api_sync_system_role_permissions')
def sync_system_role_permissions_after_migrate(sender, **kwargs):
    if sender.name != 'apps.roles_api':
        return

    try:
        synced = sync_all_default_role_permissions()
    except Exception:
        logger.exception("Failed to sync default role permissions after migrations")
        return

    if synced:
        logger.info("Default role permissions synced after migrations: %s", synced)
