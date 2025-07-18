from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from .models import UserSubscription
from .utils import log_subscription_event
from dateutil.relativedelta import relativedelta
from django.db.models import Q


@shared_task
def deactivate_expired_subscriptions():
    now = timezone.now()
    expired_subs = UserSubscription.objects.filter(
        is_active=True,
        end_date__lt=now , 
        auto_renew=True)
    

    for sub in expired_subs:
        print(f"[DEBUG] Procesando sub expirado de {sub.user.email} con end={sub.end_date}")

        sub.is_active = False
        sub.save()
        print(f"Verificando sub: user={sub.user.email}, end={sub.end_date}, auto_renew={sub.auto_renew}, is_active={sub.is_active}")



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
            print(f"[DEBUG] NUEVA sub creada con ID={new_sub.id} para {new_sub.user.email}")
            log_subscription_event(
                user=sub.user,
                subscription=new_sub,
                action="renewed",
                description="Suscripción renovada automáticamente."
            )
            
def renew_subscriptions():
    """
    Renueva automáticamente suscripciones si tienen auto_renew.
    """
    now = timezone.now()
    renewables = UserSubscription.objects.filter(
        Q(end_date__lt=now) & Q(auto_renew=True) & Q(is_active=True)
    )
    for sub in renewables:
        sub.start_date = now
        sub.end_date = now + timedelta(days=30)
        sub.save()