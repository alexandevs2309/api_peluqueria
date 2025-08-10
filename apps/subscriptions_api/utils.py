from .models import SubscriptionAuditLog, UserSubscription 
from django.utils.timezone import now

def log_subscription_event(user, action, description , subscription ):
    SubscriptionAuditLog.objects.create(
        user=user,
        subscription = subscription,
        action=action,
        description=description
    )


def get_active_subscription_for_user(user):
    return (
        UserSubscription.objects
        .filter(user=user, is_active=True, end_date__gte=now())
        .order_by('-end_date')
        .first()
    )

def get_user_active_subscription(user):
    return UserSubscription.objects.filter(user=user , is_active=True).order_by('-end_date').first()

def get_user_feature_flag(user , feature_name):
    sub = get_user_active_subscription(user)

    if sub and sub.plan and sub.plan.features:
        return sub.plan.features.get(feature_name , False)
    return False