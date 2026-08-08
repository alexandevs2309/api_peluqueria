"""
EJEMPLO DE APLICACIÓN DEL DECORADOR tenant_required_task

Este archivo muestra cómo migrar tasks existentes para validar tenant activo.
NO reemplaza tasks.py existentes, solo documenta el patrón recomendado.
"""

from celery import shared_task
from apps.tenants_api.decorators import tenant_required_task
from apps.tenants_api.utils import get_active_tenant
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# PATRÓN ANTIGUO (sin validación de tenant)
# ============================================================================

@shared_task
def process_tenant_report_OLD(tenant_id):
    """
    ⚠️ PATRÓN ANTIGUO: No valida si tenant está activo
    """
    from apps.tenants_api.models import Tenant
    
    tenant = Tenant.objects.get(id=tenant_id)  # ⚠️ Puede obtener tenant eliminado
    
    # Procesar reporte...
    logger.info(f"Processing report for {tenant.name}")


# ============================================================================
# PATRÓN NUEVO (con decorador)
# ============================================================================

@shared_task
@tenant_required_task
def process_tenant_report(tenant_id):
    """
    ✅ PATRÓN NUEVO: Valida automáticamente que tenant esté activo
    
    Si tenant está eliminado o inactivo, la task se aborta automáticamente.
    """
    from apps.tenants_api.models import Tenant
    
    # Aquí tenant ya está validado por el decorador
    tenant = Tenant.objects.get(id=tenant_id)
    
    # Procesar reporte...
    logger.info(f"Processing report for {tenant.name}")


# ============================================================================
# PATRÓN ALTERNATIVO (validación manual)
# ============================================================================

@shared_task
def process_tenant_report_MANUAL(tenant_id):
    """
    ✅ PATRÓN ALTERNATIVO: Validación manual explícita
    
    Usar cuando se necesita lógica personalizada al detectar tenant inactivo.
    """
    try:
        tenant = get_active_tenant(tenant_id)
    except Exception as e:
        logger.warning(f"Task aborted: Tenant {tenant_id} is inactive - {str(e)}")
        return None
    
    # Procesar reporte...
    logger.info(f"Processing report for {tenant.name}")


# ============================================================================
# EJEMPLO REAL: Migración de check_trial_expirations
# ============================================================================

@shared_task
def check_trial_expirations_HARDENED():
    """
    ✅ Versión mejorada de check_trial_expirations con validación de tenant
    
    CAMBIOS:
    - Filtra tenants con deleted_at__isnull=True
    - Valida tenant antes de procesar
    """
    from django.utils import timezone
    from apps.tenants_api.models import Tenant
    from apps.subscriptions_api.models import UserSubscription
    
    today = timezone.now().date()
    
    # ✅ Filtrar solo tenants activos (no eliminados)
    expired_trials = Tenant.objects.filter(
        subscription_status='trial',
        trial_end_date__lt=today,
        is_active=True,
        deleted_at__isnull=True  # ✅ Agregar este filtro
    )
    
    suspended_count = 0
    for tenant in expired_trials:
        # ✅ Validar nuevamente antes de procesar (defensa en profundidad)
        try:
            tenant = get_active_tenant(tenant.id)
        except Exception:
            logger.warning(f"Skipping tenant {tenant.id}: inactive during processing")
            continue
        
        # Suspender tenant
        tenant.subscription_status = 'suspended'
        tenant.is_active = False
        tenant.save()
        
        # Desactivar suscripción del usuario
        UserSubscription.objects.filter(
            user=tenant.owner,
            is_active=True
        ).update(is_active=False)
        
        suspended_count += 1
        logger.info(f"Trial expired for tenant {tenant.name} (ID: {tenant.id})")
    
    logger.info(f"Processed {suspended_count} expired trials")
    return f"Suspended {suspended_count} tenants with expired trials"


# ============================================================================
# RECOMENDACIONES DE MIGRACIÓN
# ============================================================================

"""
CÓMO MIGRAR TASKS EXISTENTES:

1. IDENTIFICAR tasks que reciben tenant_id como parámetro
2. AGREGAR import:
   from apps.tenants_api.decorators import tenant_required_task
   from apps.tenants_api.utils import get_active_tenant

3. OPCIÓN A - Usar decorador (simple):
   @shared_task
   @tenant_required_task
   def my_task(tenant_id, ...):
       ...

4. OPCIÓN B - Validación manual (control fino):
   @shared_task
   def my_task(tenant_id, ...):
       try:
           tenant = get_active_tenant(tenant_id)
       except Exception:
           logger.warning(f"Task aborted: Tenant {tenant_id} inactive")
           return None
       ...

5. AGREGAR filtro deleted_at__isnull=True en queries:
   Tenant.objects.filter(..., deleted_at__isnull=True)

NO MIGRAR TODAS LAS TASKS DE GOLPE.
Migrar progresivamente según prioridad.
"""
