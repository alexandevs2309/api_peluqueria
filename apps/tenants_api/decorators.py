"""
Decoradores para Celery tasks con validación de tenant
"""
from functools import wraps
import logging
from .utils import get_active_tenant

logger = logging.getLogger(__name__)


def tenant_required_task(func):
    """
    Decorador para tasks que requieren tenant activo.
    
    El primer argumento de la task debe ser tenant_id.
    Si el tenant está eliminado o inactivo, la task se aborta.
    
    Ejemplo:
        @shared_task
        @tenant_required_task
        def process_tenant_data(tenant_id, data):
            # tenant ya está validado aquí
            pass
    """
    @wraps(func)
    def wrapper(tenant_id, *args, **kwargs):
        try:
            tenant = get_active_tenant(tenant_id)
            logger.info(f"Task {func.__name__} executing for tenant {tenant.name} (ID: {tenant_id})")
            return func(tenant_id, *args, **kwargs)
        except Exception as e:
            logger.warning(f"Task {func.__name__} aborted: Tenant {tenant_id} is inactive or deleted - {str(e)}")
            return None
    
    return wrapper
