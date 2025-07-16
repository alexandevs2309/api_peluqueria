from celery import shared_task
from django.utils import timezone
from .models import UserSubscription
from .utils import log_subscription_event
from dateutil.relativedelta import relativedelta

@shared_task
def deactivate_expired_subscriptions():
    now = timezone.now()
    expired_subs = UserSubscription.objects.filter(is_active=True, end_date__lt=now , auto_renew=True)
    
    print(f"Expired subscriptions found: {expired_subs.count()}")

    for sub in expired_subs:
        sub.is_active = False
        sub.save()

        log_subscription_event(
            user=sub.user,
            subscription=sub,
            action="expired",
            description="La suscripción expiró automáticamente."
        )

        if sub.auto_renew:
            new_sub = UserSubscription.objects.create(
                user=sub.user,
                plan=sub.plan,
                start_date=now,
                end_date=now + relativedelta(months=sub.plan.duration_month),
                is_active=True,
                auto_renew=sub.auto_renew,
                
            )

            log_subscription_event(
                user=sub.user,
                subscription=new_sub,
                action="renewed",
                description="Suscripción renovada automáticamente."
            )
