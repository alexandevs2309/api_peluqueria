from .models import SystemSettings
from django.core.cache import cache
from django.utils import timezone
from apps.subscriptions_api.plan_consistency import build_plan_settings_snapshot, is_unlimited_limit


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

    config = get_system_config()
    # Excluir tenants eliminados lógicamente del límite global
    current_count = Tenant.objects.filter(deleted_at__isnull=True).count()
    return current_count < config.max_tenants


def validate_employee_limit(tenant, plan_type='basic'):
    """Validar límite de empleados por plan"""
    if tenant is None:
        return False

    current_count = tenant.employees.filter(is_active=True).count() if hasattr(tenant, 'employees') else 0

    tenant_limit = getattr(tenant, 'max_employees', None)
    if tenant_limit is not None:
        if is_unlimited_limit(tenant_limit):
            return True
        return current_count < tenant_limit

    config = get_system_config()
    plan_limits = {
        'basic': config.basic_plan_max_employees,
        'standard': config.premium_plan_max_employees,
        'premium': config.premium_plan_max_employees,
        'enterprise': config.enterprise_plan_max_employees,
    }
    return current_count < plan_limits.get(plan_type, config.basic_plan_max_employees)


def _get_next_upgrade_plan(tenant, capacity_field, current_limit):
    from apps.subscriptions_api.models import SubscriptionPlan

    active_plans = list(SubscriptionPlan.objects.filter(is_active=True))
    if not active_plans:
        return None

    priority = {'free': 0, 'basic': 1, 'standard': 2, 'premium': 3, 'enterprise': 4}
    current_plan = getattr(tenant, 'subscription_plan', None)
    current_plan_name = getattr(current_plan, 'name', None) or getattr(tenant, 'plan_type', 'free')

    def plan_sort_key(plan):
        return (priority.get(plan.name, 99), getattr(plan, capacity_field, 0))

    ordered_plans = sorted(active_plans, key=plan_sort_key)
    return next(
        (
            plan for plan in ordered_plans
            if priority.get(plan.name, 99) > priority.get(current_plan_name, -1)
            and (
                getattr(plan, capacity_field, 0) == 0
                or getattr(plan, capacity_field, 0) > current_limit
            )
        ),
        None
    )


def _apply_auto_upgrade(tenant, next_plan, changed_by, trigger, current_count, previous_limit):
    from apps.subscriptions_api.models import UserSubscription, Subscription, SubscriptionAuditLog
    from apps.audit_api.models import AuditLog

    current_plan = getattr(tenant, 'subscription_plan', None)
    old_plan_name = getattr(current_plan, 'name', None) or getattr(tenant, 'plan_type', 'free')

    tenant.subscription_plan = next_plan
    tenant.plan_type = next_plan.name
    tenant.max_employees = next_plan.max_employees
    tenant.max_users = next_plan.max_users
    tenant.settings.update(
        build_plan_settings_snapshot(next_plan, inherited_at=str(timezone.now()))
    )
    tenant.settings.update({
        'plan_type_logic': f'Plan {next_plan.name} aplicado por auto_upgrade_limits',
        'auto_upgraded_at': str(timezone.now()),
        'auto_upgrade_trigger': trigger,
    })
    tenant.save(update_fields=[
        'subscription_plan',
        'plan_type',
        'max_employees',
        'max_users',
        'settings',
        'updated_at',
    ])

    active_subscription = Subscription.objects.filter(tenant=tenant, is_active=True).first()
    if active_subscription and not Subscription.objects.filter(
        tenant=tenant,
        plan=next_plan
    ).exclude(pk=active_subscription.pk).exists():
        active_subscription.plan = next_plan
        active_subscription.save(update_fields=['plan'])

    active_user_subscriptions = UserSubscription.objects.filter(user__tenant=tenant, is_active=True)
    for user_subscription in active_user_subscriptions:
        previous_plan = user_subscription.plan
        user_subscription.plan = next_plan
        user_subscription.save(update_fields=['plan'])
        SubscriptionAuditLog.objects.create(
            user=user_subscription.user,
            subscription=user_subscription,
            action='plan_changed',
            description=f'Plan cambiado automáticamente de {previous_plan.name} a {next_plan.name} por {trigger}'
        )

    AuditLog.objects.create(
        user=changed_by if getattr(changed_by, 'is_authenticated', False) else None,
        action='SUBSCRIPTION_UPDATE',
        description=f'Auto upgrade de límites para tenant {tenant.name}: {old_plan_name} -> {next_plan.name}',
        source='SUBSCRIPTIONS',
        extra_data={
            'tenant_id': tenant.id,
            'old_plan': old_plan_name,
            'new_plan': next_plan.name,
            'trigger': trigger,
            'current_count': current_count,
            'previous_limit': previous_limit,
            'new_employee_limit': next_plan.max_employees,
            'new_user_limit': next_plan.max_users,
        }
    )

    clear_system_config_cache()
    return {
        'upgraded': True,
        'old_plan': old_plan_name,
        'new_plan': next_plan.name,
        'new_limit': 0 if trigger == 'employee_limit' and next_plan.max_employees == 0 else (
            next_plan.max_employees if trigger == 'employee_limit' else next_plan.max_users
        ),
    }


def maybe_auto_upgrade_employee_limit(tenant, changed_by=None):
    """
    Si auto_upgrade_limits está activo y el tenant alcanzó el límite actual
    de empleados, promueve al siguiente plan disponible con mayor capacidad.
    """
    if tenant is None:
        return {'upgraded': False, 'reason': 'missing_tenant'}

    config = get_system_config()
    if not config.auto_upgrade_limits:
        return {'upgraded': False, 'reason': 'disabled'}

    current_limit = getattr(tenant, 'max_employees', 0)
    if is_unlimited_limit(current_limit):
        return {'upgraded': False, 'reason': 'already_unlimited'}

    current_count = tenant.employees.filter(is_active=True).count() if hasattr(tenant, 'employees') else 0
    if current_count < current_limit:
        return {'upgraded': False, 'reason': 'below_limit'}

    next_plan = _get_next_upgrade_plan(tenant, 'max_employees', current_limit)
    if next_plan is None:
        return {'upgraded': False, 'reason': 'no_higher_plan'}
    return _apply_auto_upgrade(tenant, next_plan, changed_by, 'employee_limit', current_count, current_limit)


def maybe_auto_upgrade_user_limit(tenant, changed_by=None):
    """
    Si auto_upgrade_limits está activo y el tenant alcanzó el límite actual
    de usuarios, promueve al siguiente plan disponible con mayor capacidad.
    """
    if tenant is None:
        return {'upgraded': False, 'reason': 'missing_tenant'}

    config = get_system_config()
    if not config.auto_upgrade_limits:
        return {'upgraded': False, 'reason': 'disabled'}

    current_limit = getattr(tenant, 'max_users', 0)
    if is_unlimited_limit(current_limit):
        return {'upgraded': False, 'reason': 'already_unlimited'}

    current_count = tenant.users.filter(is_active=True).count() if hasattr(tenant, 'users') else 0
    if current_count < current_limit:
        return {'upgraded': False, 'reason': 'below_limit'}

    next_plan = _get_next_upgrade_plan(tenant, 'max_users', current_limit)
    if next_plan is None:
        return {'upgraded': False, 'reason': 'no_higher_plan'}

    return _apply_auto_upgrade(tenant, next_plan, changed_by, 'user_limit', current_count, current_limit)


def get_trial_period_days():
    """Obtener días de período de prueba"""
    config = get_system_config()
    return config.trial_days


def is_integration_enabled(integration_name):
    """Verificar si una integración está habilitada"""
    config = get_system_config()
    return getattr(config, f'{integration_name}_enabled', False)
