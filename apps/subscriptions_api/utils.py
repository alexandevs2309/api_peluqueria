from datetime import timedelta
from django.utils import timezone
from apps.settings_api.utils import get_trial_period_days
from .plan_consistency import get_feature_value


def create_trial_subscription(tenant, plan):
    """Crear suscripción con período de prueba basado en configuraciones"""
    from .models import Subscription

    trial_days = get_trial_period_days()
    trial_end = timezone.now() + timedelta(days=trial_days)

    return Subscription.objects.create(
        tenant=tenant,
        plan=plan,
        status='trial',
        trial_end=trial_end,
        is_active=True
    )


def get_user_active_subscription(user):
    """Obtener suscripción activa del usuario"""
    from .models import UserSubscription

    return UserSubscription.objects.filter(
        user=user,
        is_active=True
    ).first()


def get_user_feature_flag(user, feature_name):
    """Verificar si el usuario tiene acceso a una funcionalidad"""
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    subscription = get_user_active_subscription(user)
    if not subscription:
        return False

    features = getattr(subscription.plan, 'features', None) or {}
    if isinstance(features, dict) and feature_name in features:
        return get_feature_value(features, feature_name, default=False)

    plan_features = {
        'basic': ['pos_enabled', 'appointments_enabled'],
        'standard': ['pos_enabled', 'appointments_enabled', 'reports_enabled', 'inventory_enabled', 'promotions_enabled'],
        'premium': ['pos_enabled', 'appointments_enabled', 'reports_enabled', 'inventory_enabled', 'promotions_enabled'],
        'enterprise': ['pos_enabled', 'appointments_enabled', 'reports_enabled', 'inventory_enabled', 'export_enabled', 'promotions_enabled']
    }

    plan_type = getattr(subscription.plan, 'name', 'basic').lower()
    return feature_name in plan_features.get(plan_type, [])


def log_subscription_event(*args, **kwargs):
    """Registrar eventos de suscripción en SubscriptionAuditLog."""
    from .models import SubscriptionAuditLog

    user = kwargs.get('user')
    subscription = kwargs.get('subscription')
    action = kwargs.get('action') or kwargs.get('event_type')
    description = kwargs.get('description') or ''

    # Compatibilidad con firma posicional: (subscription, event_type, details=None)
    if subscription is None and len(args) >= 2:
        subscription = args[0]
        action = args[1]
        description = description or (args[2] if len(args) > 2 else '')

    if user is None and subscription is not None:
        user = getattr(subscription, 'user', None)

    try:
        SubscriptionAuditLog.objects.create(
            user=user,
            subscription=subscription,
            action=action or 'subscription_event',
            description=description,
        )
    except Exception:
        pass


def apply_paid_access(tenant, user, plan, months, auto_renew=False,
                      access_until_override=None, billing_interval='month'):
    """
    Activa o renueva el acceso de un tenant tras confirmar un pago.

    Función standalone para ser reutilizada desde vistas, webhooks y tasks
    sin acoplar módulos entre sí.

    - Extiende access_until desde el valor actual si está en el futuro.
    - Cambia subscription_status a 'active', is_active a True.
    - Crea un nuevo registro UserSubscription activo (si user está disponible).
    - Es idempotente: ejecutarla dos veces produce el mismo estado final.

    Args:
        tenant:                Instancia de Tenant a activar.
        user:                  Usuario titular (puede ser None).
        plan:                  Instancia de SubscriptionPlan.
        months:                Meses de acceso a conceder.
        auto_renew:            Si la suscripción es recurrente.
        access_until_override: Fecha exacta de expiración (omite el cálculo).
        billing_interval:      'month' o 'year'.

    Returns:
        datetime: Nueva fecha de expiración (access_until).
    """
    import logging
    from dateutil.relativedelta import relativedelta
    from django.utils import timezone as tz
    from apps.subscriptions_api.models import UserSubscription

    _logger = logging.getLogger(__name__)

    now = tz.now()
    base_time = now
    if tenant.access_until and tenant.access_until > now:
        base_time = tenant.access_until

    access_until = access_until_override or (base_time + relativedelta(months=months))

    tenant.subscription_plan = plan
    tenant.subscription_status = 'active'
    tenant.trial_end_date = None
    tenant.is_active = True
    tenant.access_until = access_until
    if plan:
        tenant.plan_type = plan.name
    tenant.save(update_fields=[
        'subscription_plan',
        'plan_type',
        'subscription_status',
        'trial_end_date',
        'is_active',
        'access_until',
        'updated_at',
    ])

    if user:
        UserSubscription.objects.filter(user=user, is_active=True).update(
            is_active=False,
            end_date=now,
        )
        UserSubscription.objects.create(
            user=user,
            plan=plan,
            start_date=base_time,
            end_date=access_until,
            is_active=True,
            auto_renew=auto_renew,
            billing_interval=billing_interval,
        )

    _logger.info(
        'apply_paid_access: tenant=%s plan=%s access_until=%s auto_renew=%s',
        tenant.id, plan.name if plan else None, access_until, auto_renew,
    )
    return access_until
