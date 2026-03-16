from datetime import timedelta
from django.utils import timezone
from apps.settings_api.utils import get_trial_period_days


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
        return bool(features.get(feature_name, False))

    plan_features = {
        'basic': ['pos_enabled', 'appointments_enabled'],
        'standard': ['pos_enabled', 'appointments_enabled', 'reports_enabled', 'inventory_enabled'],
        'premium': ['pos_enabled', 'appointments_enabled', 'reports_enabled', 'inventory_enabled'],
        'enterprise': ['pos_enabled', 'appointments_enabled', 'reports_enabled', 'inventory_enabled', 'export_enabled', 'api_access']
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
