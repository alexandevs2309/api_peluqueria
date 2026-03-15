from .models import SystemSettings
from django.core.cache import cache


def get_system_config():
    """Obtener configuraciones del sistema con cache"""
    config = cache.get('system_settings')
    if not config:
        config = SystemSettings.get_settings()
        cache.set('system_settings', config, 300)  # 5 minutos
    return config


def clear_system_config_cache():
    """Limpiar cache de configuraciones"""
    cache.delete('system_settings')


def validate_tenant_limit():
    """Validar si se puede crear un nuevo tenant"""
    from apps.tenants_api.models import Tenant
    current_count = tenant.employees.filter(is_active=True).count() if hasattr(tenant, 'employees') else 0

    plan = getattr(tenant, 'subscription_plan', None)
    if plan is not None and hasattr(plan, 'max_employees'):
        plan_limit = plan.max_employees
        if plan_limit == 0:
            return True
        return current_count < plan_limit

    tenant_limit = getattr(tenant, 'max_employees', None)
    if tenant_limit is not None:
        if tenant_limit == 0:
            return True
        return current_count < tenant_limit

    config = get_system_config()
    # Excluir tenants eliminados lógicamente del límite global
    current_count = Tenant.objects.filter(deleted_at__isnull=True).count()
    return current_count < config.max_tenants


def validate_employee_limit(tenant, plan_type='basic'):
    """Validar límite de empleados por plan"""
    config = get_system_config()
    plan_limits = {
        'basic': config.basic_plan_max_employees,
        'standard': config.premium_plan_max_employees,
        'premium': config.premium_plan_max_employees,
        'enterprise': config.enterprise_plan_max_employees,
    }
    return current_count < plan_limits.get(plan_type, config.basic_plan_max_employees)


def get_trial_period_days():
    """Obtener días de período de prueba"""
    config = get_system_config()
    return config.trial_days


def is_integration_enabled(integration_name):
    """Verificar si una integración está habilitada"""
    config = get_system_config()
    return getattr(config, f'{integration_name}_enabled', False)
