import logging

from django.db.models.signals import post_migrate
from django.dispatch import receiver

from apps.roles_api.default_permissions import sync_all_default_role_permissions


logger = logging.getLogger(__name__)


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
