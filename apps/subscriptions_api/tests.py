import pytest
import time
from django.urls import path
from django.db.models import Q
from django.urls import reverse
from rest_framework.test import APIClient
from apps.auth_api.models import User
from apps.subscriptions_api.utils import log_subscription_event
from .models import SubscriptionPlan, UserSubscription
from datetime import date, timedelta
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from apps.subscriptions_api.tasks import deactivate_expired_subscriptions, renew_subscriptions
from apps.subscriptions_api.models import SubscriptionAuditLog
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from apps.roles_api.decorators import check_active_subscription




@pytest.mark.django_db
def test_create_subscription_plan_as_admin():
    admin = User.objects.create_superuser(email="admin@test.com", password="pass")
    client = APIClient()
    client.force_authenticate(admin)
    
    response = client.post(reverse("subscription-plan-list"), {
        "name": "basic",
        "description": "1 mes",
        "price": "19.99",
        "duration_month": 1
    })

    assert response.status_code == 201
    assert SubscriptionPlan.objects.count() == 1

@pytest.mark.django_db
def test_user_subscription_creation():
    user = User.objects.create_user(email="user@test.com", password="pass")
    plan = SubscriptionPlan.objects.create(name="basic", description="test", price=10, duration_month=1)
    
    client = APIClient()
    client.force_authenticate(user)
    
    response = client.post(reverse("user-subscription-list"), {
        "plan": plan.id,
        "end_date": (date.today() + timedelta(days=30)).isoformat()
    })

    assert response.status_code == 201
    assert UserSubscription.objects.filter(user=user).exists()


@pytest.fixture
def subscription_plans():
    return {
        'basic': SubscriptionPlan.objects.create(name='basic', price=10.00, duration_month=1),
        'standard': SubscriptionPlan.objects.create(name='standard', price=25.00, duration_month=3),
        'premium': SubscriptionPlan.objects.create(name='premium', price=80.00, duration_month=12),
    }

@pytest.fixture
def user(db):
    return User.objects.create_user(email='test@example.com', password='test1234')


@pytest.fixture
def user_subscription(db):
    user = User.objects.create_user(email="auditlog@example.com", password="12345678")
    plan = SubscriptionPlan.objects.create(name="Básico", price=0, duration_month=1)
    subscription = UserSubscription.objects.create(
        user=user,
        plan=plan,
        start_date=timezone.now(),
        end_date=timezone.now() + timezone.timedelta(days=30),
        is_active=True
    )
    return subscription



@pytest.mark.django_db
def test_basic_subscription_duration(user, subscription_plans):
    plan = subscription_plans['basic']
    subscription = UserSubscription.objects.create(user=user, plan=plan)
    expected_end = subscription.start_date + relativedelta(months=1)
    assert subscription.end_date.date() == expected_end.date()

@pytest.mark.django_db
def test_standard_subscription_duration(user, subscription_plans):
    plan = subscription_plans['standard']
    subscription = UserSubscription.objects.create(user=user, plan=plan)
    expected_end = subscription.start_date + relativedelta(months=3)
    assert subscription.end_date.date() == expected_end.date()

@pytest.mark.django_db
def test_premium_subscription_duration(user, subscription_plans):
    plan = subscription_plans['premium']
    subscription = UserSubscription.objects.create(user=user, plan=plan)
    expected_end = subscription.start_date + relativedelta(months=12)
    assert subscription.end_date.date() == expected_end.date()


@pytest.mark.django_db
def test_subscription_audit_log_created_on_cancel(user_subscription):
    subscription = user_subscription
    user = subscription.user
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(f"/api/subscriptions/user-subscriptions/{subscription.pk}/cancel/")
    assert response.status_code == 200

    from apps.subscriptions_api.models import SubscriptionAuditLog
    logs = SubscriptionAuditLog.objects.filter(user=user)
    assert logs.exists()
    assert logs.first().action == 'cancelled'


@pytest.mark.django_db
def test_subscription_audit_log_on_creation():
    user = User.objects.create_user(email="audit@created.com", password="123456")
    plan = SubscriptionPlan.objects.create(name="Básico", price=0, duration_month=1)

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(reverse("user-subscription-list"), {
        "plan": plan.id
    })

    assert response.status_code == 201

    from apps.subscriptions_api.models import SubscriptionAuditLog
    logs = SubscriptionAuditLog.objects.filter(user=user)
    assert logs.exists()
    assert logs.first().action == "created"


@pytest.mark.django_db
def test_get_current_user_subscription():
    user = User.objects.create_user(email="user@example.com", password="test1234")
    plan = SubscriptionPlan.objects.create(name="basic", price=10, duration_month=1)
    subscription = UserSubscription.objects.create(user=user, plan=plan)

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("user-subscription-current"))
    assert response.status_code == 200
    assert response.data["plan"] == plan.id
    assert response.data["is_active"] is True



@pytest.mark.django_db
def test_subscription_auto_renew_creates_new_subscription():
    user = User.objects.create_user(email="renew@test.com", password="pass")
    plan = SubscriptionPlan.objects.create(name="Pro", price=0, duration_month=1)

    # Crear suscripción expirada, pero activa
    old_sub = UserSubscription.objects.create(
        user=user,
        plan=plan,
        start_date=timezone.now() - timedelta(days=40),
        end_date=timezone.now() - timedelta(days=10),
        is_active=False,  # evitar que save() la desactive automáticamente
        auto_renew=True,
    )
    # Forzar is_active sin activar la lógica de .save()
    UserSubscription.objects.filter(pk=old_sub.pk).update(is_active=True)

    print("Antes de la tarea:")
    for s in UserSubscription.objects.all():
        print(f"ID={s.id}, active={s.is_active}, end={s.end_date}, auto_renew={s.auto_renew}")

    # Ejecutar tarea
    deactivate_expired_subscriptions()

    print("Después de la tarea:")
    for s in UserSubscription.objects.all():
        print(f"ID={s.id}, active={s.is_active}, end={s.end_date}, auto_renew={s.auto_renew}")

    old_sub.refresh_from_db()
    assert not old_sub.is_active, "La suscripción antigua debería haber sido desactivada."

    new_subs = UserSubscription.objects.filter(user=user, is_active=True)
    assert new_subs.count() == 1, "Debería haberse creado una nueva suscripción activa."

    new_sub = new_subs.first()
    assert new_sub.start_date > old_sub.end_date
    assert new_sub.auto_renew is True

    logs = SubscriptionAuditLog.objects.filter(user=user, action="renewed")
    assert logs.exists(), "Debería haberse creado un log de renovación."



@pytest.mark.django_db
def test_cannot_create_multiple_active_subscriptions():
    user = User.objects.create_user(email="unique@test.com", password="1234")
    plan = SubscriptionPlan.objects.create(name="Pro", price=0, duration_month=1)

    UserSubscription.objects.create(user=user, plan=plan, is_active=True)

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(reverse("user-subscription-list"), {
        "plan": plan.id
    })

    assert response.status_code == 400
    assert "subscripcion activa" in str(response.data).lower()


@pytest.mark.django_db
def test_cannot_reactivate_cancelled_subscription():
    user = User.objects.create_user(email="cancel@test.com", password="1234")
    plan = SubscriptionPlan.objects.create(name="Test", price=0, duration_month=1)
    sub = UserSubscription.objects.create(user=user, plan=plan, is_active=False)

    sub.is_active = True
    with pytest.raises(ValueError, match="No se puede reactivar"):
        sub.save()


@pytest.mark.django_db
def test_deactivate_and_renew_subscription(user):
    plan = SubscriptionPlan.objects.create(
        name="Premium",
        price=100,
        duration_month=1,
        max_employees=10
    )

    now = timezone.now()

    expired = UserSubscription.objects.create(
        user=user,
        plan=plan,
        start_date=now - relativedelta(months=2),
        end_date=now - timezone.timedelta(days=2),
        is_active=False,  # desactivado por defecto
        auto_renew=True
    )
    # Forzar activación por fuera del .save()
    UserSubscription.objects.filter(pk=expired.pk).update(is_active=True)

    print("[TEST DEBUG] antes de task")
    for s in UserSubscription.objects.all():
        print(f"ID={s.id}, user={s.user.email}, active={s.is_active}, end={s.end_date}, auto_renew={s.auto_renew}")

    deactivate_expired_subscriptions()

    expired.refresh_from_db()
    assert not expired.is_active

    new_subs = UserSubscription.objects.filter(user=user, is_active=True).exclude(id=expired.id)
    assert new_subs.exists(), "No se creó nueva suscripción"

    new_sub = new_subs.first()
    assert new_sub.start_date > expired.end_date
    assert new_sub.plan == plan
    assert new_sub.auto_renew


    # Vista protegida usando el decorador
@api_view(["GET"])
@check_active_subscription
def protected_view(request):
    return Response({"detail": "Acceso permitido"}, status=status.HTTP_200_OK)

# Inyección dinámica para urls de prueba
urlpatterns = [
    path("api/protected/", protected_view, name="protected-view"),
]

@pytest.fixture
def client_with_urls(settings):
    settings.ROOT_URLCONF = __name__
    return APIClient()

@pytest.mark.django_db
def test_access_denied_without_active_subscription(client_with_urls):
    user = User.objects.create_user(email="test@noactive.com", password="123456")
    client_with_urls.force_authenticate(user=user)
    response = client_with_urls.get("/api/protected/")
    assert response.status_code == 403
    assert "requiere una suscripción activa" in response.data["detail"].lower()

@pytest.mark.django_db
def test_access_allowed_with_active_subscription(client_with_urls):
    user = User.objects.create_user(email="test@active.com", password="123456")
    plan = SubscriptionPlan.objects.create(name="Basic", price=10, duration_month=1)
    UserSubscription.objects.create(
        user=user,
        plan=plan,
        start_date=timezone.now() - timezone.timedelta(days=1),
        end_date=timezone.now() + timezone.timedelta(days=30),
        is_active=True
    )
    client_with_urls.force_authenticate(user=user)
    response = client_with_urls.get("/api/protected/")
    assert response.status_code == 200
    assert response.data["detail"] == "Acceso permitido"


@pytest.mark.django_db
def renew_subscriptions():
    now = timezone.now()
    renewables = UserSubscription.objects.filter(
        Q(end_date__lt=now) & Q(auto_renew=True) & Q(is_active=True)
    )
    for sub in renewables:
        sub.start_date = now
        sub.end_date = now + relativedelta(months=sub.plan.duration_month) 
        sub.save()

        log_subscription_event(
            user=sub.user,
            subscription=sub,
            action="renewed",
            description="Suscripción renovada automáticamente."
        )


