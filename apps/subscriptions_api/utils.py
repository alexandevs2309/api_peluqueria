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
        
    # SuperAdmin tiene acceso a todo
    if user.is_superuser:
        return True
        
    # Verificar suscripción activa
    subscription = get_user_active_subscription(user)
    if not subscription:
        return False
        
    # Verificar funcionalidades según el plan
    plan_features = {
        'basic': ['pos_enabled', 'appointments_enabled'],
        'premium': ['pos_enabled', 'appointments_enabled', 'reports_enabled', 'inventory_enabled'],
        'enterprise': ['pos_enabled', 'appointments_enabled', 'reports_enabled', 'inventory_enabled', 'export_enabled', 'api_access']
    }
    
    plan_type = getattr(subscription.plan, 'name', 'basic').lower()
    return feature_name in plan_features.get(plan_type, [])


def log_subscription_event(subscription, event_type, details=None):
    """Registrar eventos de suscripción"""
    from django.contrib.contenttypes.models import ContentType
    from apps.audit_api.models import AuditLog
    
    try:
        AuditLog.objects.create(
            action=event_type,
            description=f"Subscription {event_type}: {subscription.tenant.name if subscription.tenant else 'Unknown'}",
            content_type=ContentType.objects.get_for_model(subscription),
            object_id=subscription.id,
            source='SYSTEM',
            extra_data=details or {}
        )
    except Exception:
        # Si falla el log, no interrumpir el flujo
        pass