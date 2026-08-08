"""
Utilidades para manejo de tenants en tasks y webhooks
"""
from django.core.exceptions import ObjectDoesNotExist
from .models import Tenant


def get_active_tenant(tenant_id):
    """
    Obtiene un tenant activo y no eliminado.
    
    Raises:
        Tenant.DoesNotExist: Si el tenant no existe, está eliminado o inactivo
    """
    return Tenant.objects.get(
        id=tenant_id,
        deleted_at__isnull=True,
        is_active=True
    )


def is_tenant_active(tenant_id):
    """
    Verifica si un tenant está activo sin lanzar excepción.
    
    Returns:
        bool: True si el tenant está activo, False en caso contrario
    """
    try:
        get_active_tenant(tenant_id)
        return True
    except ObjectDoesNotExist:
        return False
