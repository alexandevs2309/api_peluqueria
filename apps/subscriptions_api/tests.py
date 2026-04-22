import pytest
from functools import wraps
from io import StringIO
from django.urls import path
from django.db.models import Q
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.management import call_command
from rest_framework.test import APIClient
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta

from apps.auth_api.models import User
from apps.tenants_api.models import Tenant
from apps.employees_api.models import Employee
from apps.subscriptions_api.access_control import has_feature
from apps.subscriptions_api.utils import log_subscription_event
from apps.subscriptions_api.tasks import check_expired_subscriptions as deactivate_expired_subscriptions
from apps.subscriptions_api.models import Subscription, SubscriptionAuditLog, SubscriptionPlan, UserSubscription
from apps.subscriptions_api.plan_consistency import can_add_employee, can_add_user, tenant_has_feature
from apps.subscriptions_api import views as subscription_views


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(suffix: str, owner=None) -> Tenant:
    plan, _ = SubscriptionPlan.objects.get_or_create(
        name="basic", defaults={"price": 10, "duration_month": 1, "stripe_price_id": "price_test_123"}
    )
    if not plan.stripe_price_id:
        plan.stripe_price_id = "price_test_123"
        plan.save(update_fields=["stripe_price_id"])
    return Tenant.objects.create(
        name=f"Tenant {suffix}",
        subdomain=f"tenant-{suffix}",
        owner=owner,
        subscription_plan=plan,
        subscription_status="active",
        is_active=True,
    )


def _make_simple_user(suffix: str, tenant=None) -> User:
    """Crea un usuario no-superadmin con los campos requeridos por el modelo."""
    if tenant is None:
        owner = User.objects.create_superuser(
            email=f"owner_{suffix}@test.com",
            password="pass",
            full_name="Owner",
        )
        tenant = _make_tenant(suffix, owner=owner)
    return User.objects.create_user(
        email=f"user_{suffix}@test.com",
        password="pass",
        full_name=f"User {suffix}",
        tenant=tenant,
        role="Client-Admin",
    )


def _make_tenant_user(suffix: str):
    owner = User.objects.create_superuser(
        email=f"owner_{suffix}@test.com",
        password="pass",
        full_name="Owner",
    )
    tenant = _make_tenant(suffix, owner=owner)
    user = User.objects.create_user(
        email=f"user_{suffix}@test.com",
        password="pass",
        full_name="User",
        tenant=tenant,
        role="Client-Admin",
    )
    return user, tenant


# ---------------------------------------------------------------------------
# Decorador inline para tests de acceso
# ---------------------------------------------------------------------------

def check_active_subscription(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        has_active = UserSubscription.objects.filter(
            user=request.user,
            is_active=True,
            end_date__gte=timezone.now(),
        ).exists()
        if not has_active:
            return Response(
                {"detail": "Esta acción requiere una suscripción activa."},
                status=403,
            )
        return view_func(request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def subscription_plans(db):
    return {
        "basic": SubscriptionPlan.objects.get_or_create(name="basic", defaults={"price": 10.00, "duration_month": 1})[0],
        "standard": SubscriptionPlan.objects.get_or_create(name="standard", defaults={"price": 25.00, "duration_month": 3})[0],
        "premium": SubscriptionPlan.objects.get_or_create(name="premium", defaults={"price": 80.00, "duration_month": 12})[0],
    }


@pytest.fixture
def user(db):
    return _make_simple_user("fixture")


@pytest.fixture
def user_subscription(db):
    u = _make_simple_user("auditlog")
    plan = SubscriptionPlan.objects.create(name="Básico", price=0, duration_month=1)
    return UserSubscription.objects.create(
        user=u,
        plan=plan,
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(days=30),
        is_active=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_subscription_plan_as_admin():
    admin = User.objects.create_superuser(
        email="admin@test.com", password="pass", full_name="Admin"
    )
    client = APIClient()
    client.force_authenticate(admin)

    response = client.post(reverse("subscription-plan-list"), {
        "name": "basic",
        "description": "1 mes",
        "price": "19.99",
        "duration_month": 1,
    })

    assert response.status_code == 201
    assert SubscriptionPlan.objects.count() == 1


@pytest.mark.django_db
def test_user_subscription_creation():
    admin = User.objects.create_superuser(email="admin_sub@test.com", password="pass", full_name="Admin")
    plan = SubscriptionPlan.objects.get_or_create(name="basic", defaults={"description": "test", "price": 10, "duration_month": 1})[0]

    client = APIClient()
    client.force_authenticate(admin)

    response = client.post(reverse("user-subscription-list"), {
        "plan": plan.id,
        "end_date": (date.today() + timedelta(days=30)).isoformat(),
    })

    assert response.status_code == 201
    assert UserSubscription.objects.filter(user=admin).exists()


@pytest.mark.django_db
def test_basic_subscription_duration(user, subscription_plans):
    plan = subscription_plans["basic"]
    subscription = UserSubscription.objects.create(user=user, plan=plan)
    expected_end = subscription.start_date + relativedelta(months=1)
    assert subscription.end_date.date() == expected_end.date()


@pytest.mark.django_db
def test_standard_subscription_duration(user, subscription_plans):
    plan = subscription_plans["standard"]
    subscription = UserSubscription.objects.create(user=user, plan=plan)
    expected_end = subscription.start_date + relativedelta(months=3)
    assert subscription.end_date.date() == expected_end.date()


@pytest.mark.django_db
def test_premium_subscription_duration(user, subscription_plans):
    plan = subscription_plans["premium"]
    subscription = UserSubscription.objects.create(user=user, plan=plan)
    expected_end = subscription.start_date + relativedelta(months=12)
    assert subscription.end_date.date() == expected_end.date()


@pytest.mark.django_db
def test_subscription_audit_log_created_on_cancel(user_subscription):
    subscription = user_subscription
    u = subscription.user
    admin = User.objects.create_superuser(email="admin_cancel@test.com", password="pass", full_name="Admin")
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.post(f"/api/subscriptions/user-subscriptions/{subscription.pk}/cancel/")
    assert response.status_code == 200

    logs = SubscriptionAuditLog.objects.filter(user=admin)
    assert logs.exists()
    assert logs.first().action == "cancelled"


@pytest.mark.django_db
def test_subscription_audit_log_on_creation():
    admin = User.objects.create_superuser(email="admin_audit@test.com", password="pass", full_name="Admin")
    plan = SubscriptionPlan.objects.get_or_create(name="Basico", defaults={"price": 0, "duration_month": 1})[0]

    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.post(reverse("user-subscription-list"), {"plan": plan.id})
    assert response.status_code == 201

    logs = SubscriptionAuditLog.objects.filter(user=admin)
    assert logs.exists()
    assert logs.first().action == "created"


@pytest.mark.django_db
def test_get_current_user_subscription():
    admin = User.objects.create_superuser(email="admin_current@test.com", password="pass", full_name="Admin")
    plan = SubscriptionPlan.objects.get_or_create(name="basic", defaults={"price": 10, "duration_month": 1})[0]
    UserSubscription.objects.create(user=admin, plan=plan)

    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.get(reverse("user-subscription-current"))
    assert response.status_code == 200
    assert response.data["plan"] == plan.id
    assert response.data["is_active"] is True


@pytest.mark.xfail(reason="check_expired_subscriptions no implementa renovación automática, solo desactiva")
@pytest.mark.django_db
def test_subscription_auto_renew_creates_new_subscription():
    user = _make_simple_user("auto_renew")
    plan = SubscriptionPlan.objects.create(name="Pro", price=0, duration_month=1)

    old_sub = UserSubscription.objects.create(
        user=user,
        plan=plan,
        start_date=timezone.now() - timedelta(days=40),
        end_date=timezone.now() - timedelta(days=10),
        is_active=False,
        auto_renew=True,
    )
    UserSubscription.objects.filter(pk=old_sub.pk).update(is_active=True)

    deactivate_expired_subscriptions()

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
    admin = User.objects.create_superuser(email="admin_multi@test.com", password="pass", full_name="Admin")
    plan = SubscriptionPlan.objects.get_or_create(name="Pro", defaults={"price": 0, "duration_month": 1})[0]
    UserSubscription.objects.create(user=admin, plan=plan, is_active=True)

    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.post(reverse("user-subscription-list"), {"plan": plan.id})
    assert response.status_code == 400
    assert "subscripcion activa" in str(response.data).lower()


@pytest.mark.django_db
def test_cannot_reactivate_cancelled_subscription():
    user = _make_simple_user("cancel_sub")
    plan = SubscriptionPlan.objects.create(name="Test", price=0, duration_month=1)
    sub = UserSubscription.objects.create(user=user, plan=plan, is_active=False)

    sub.is_active = True
    with pytest.raises(ValueError, match="No se puede reactivar"):
        sub.save()


@pytest.mark.xfail(reason="check_expired_subscriptions no implementa renovación automática, solo desactiva")
@pytest.mark.django_db
def test_deactivate_and_renew_subscription(user):
    plan = SubscriptionPlan.objects.create(
        name="Premium", price=100, duration_month=1, max_employees=10
    )
    now = timezone.now()

    expired = UserSubscription.objects.create(
        user=user,
        plan=plan,
        start_date=now - relativedelta(months=2),
        end_date=now - timedelta(days=2),
        is_active=False,
        auto_renew=True,
    )
    UserSubscription.objects.filter(pk=expired.pk).update(is_active=True)

    deactivate_expired_subscriptions()

    expired.refresh_from_db()
    assert not expired.is_active

    new_subs = UserSubscription.objects.filter(user=user, is_active=True).exclude(id=expired.id)
    assert new_subs.exists(), "No se creó nueva suscripción"

    new_sub = new_subs.first()
    assert new_sub.start_date > expired.end_date
    assert new_sub.plan == plan
    assert new_sub.auto_renew


# ---------------------------------------------------------------------------
# Vista protegida + URL dinámica para tests de acceso
# ---------------------------------------------------------------------------

@api_view(["GET"])
@check_active_subscription
def protected_view(request):
    return Response({"detail": "Acceso permitido"}, status=status.HTTP_200_OK)


urlpatterns = [
    path("api/protected/", protected_view, name="protected-view"),
]


@pytest.fixture
def client_with_urls(settings):
    settings.ROOT_URLCONF = __name__
    return APIClient()


@pytest.mark.django_db
def test_access_denied_without_active_subscription(client_with_urls):
    user = _make_simple_user("no_active")
    client_with_urls.force_authenticate(user=user)
    response = client_with_urls.get("/api/protected/")
    assert response.status_code == 403
    assert "requiere una suscripción activa" in response.data["detail"].lower()


@pytest.mark.django_db
def test_access_allowed_with_active_subscription(client_with_urls):
    user = _make_simple_user("with_active")
    plan = SubscriptionPlan.objects.create(name="Basic", price=10, duration_month=1)
    UserSubscription.objects.create(
        user=user,
        plan=plan,
        start_date=timezone.now() - timedelta(days=1),
        end_date=timezone.now() + timedelta(days=30),
        is_active=True,
    )
    client_with_urls.force_authenticate(user=user)
    response = client_with_urls.get("/api/protected/")
    assert response.status_code == 200
    assert response.data["detail"] == "Acceso permitido"


# ---------------------------------------------------------------------------
# FakeStripeObject
# ---------------------------------------------------------------------------

class FakeStripeObject:
    def __init__(self, **kwargs):
        self._data = dict(kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get(self, key, default=None):
        return self._data.get(key, default)


# ---------------------------------------------------------------------------
# Tests Stripe (monkeypatch)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_renew_subscription_payment_intent_metadata_is_string(monkeypatch):
    user, tenant = _make_tenant_user("meta")
    plan = SubscriptionPlan.objects.get_or_create(name="basic", defaults={"price": 10, "duration_month": 1})[0]

    captured = {}

    def fake_customer_create(**kwargs):
        return FakeStripeObject(id="cus_meta")

    def fake_customer_retrieve(customer_id):
        return FakeStripeObject(id=customer_id)

    def fake_payment_intent_create(**kwargs):
        captured["metadata"] = kwargs.get("metadata") or {}
        return FakeStripeObject(
            id="pi_meta",
            status="requires_action",
            client_secret="cs_meta",
            amount=1000,
            customer=kwargs.get("customer"),
        )

    monkeypatch.setattr(subscription_views.stripe.Customer, "create", fake_customer_create)
    monkeypatch.setattr(subscription_views.stripe.Customer, "retrieve", fake_customer_retrieve)
    monkeypatch.setattr(subscription_views.stripe.PaymentIntent, "create", fake_payment_intent_create)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(reverse("renew-subscription"), {
        "plan_id": plan.id,
        "payment_method_id": "pm_test_123",
        "months": 1,
        "auto_renew": False,
    })

    assert response.status_code == 200
    assert response.data.get("requires_action") is True
    assert captured["metadata"]
    assert all(isinstance(v, str) for v in captured["metadata"].values())


@pytest.mark.django_db
def test_renew_subscription_payment_intent_requires_action_returns_conflict(monkeypatch):
    user, tenant = _make_tenant_user("pending")
    plan = SubscriptionPlan.objects.get_or_create(name="basic", defaults={"price": 10, "duration_month": 1})[0]

    def fake_customer_create(**kwargs):
        return FakeStripeObject(id="cus_pending")

    def fake_customer_retrieve(customer_id):
        return FakeStripeObject(id=customer_id)

    def fake_payment_intent_retrieve(payment_intent_id):
        return FakeStripeObject(
            id=payment_intent_id,
            status="requires_action",
            client_secret="cs_pending",
            customer="cus_pending",
            metadata={
                "user_id": str(user.id),
                "tenant_id": str(tenant.id),
                "plan_id": str(plan.id),
                "months": "1",
            },
        )

    monkeypatch.setattr(subscription_views.stripe.Customer, "create", fake_customer_create)
    monkeypatch.setattr(subscription_views.stripe.Customer, "retrieve", fake_customer_retrieve)
    monkeypatch.setattr(subscription_views.stripe.PaymentIntent, "retrieve", fake_payment_intent_retrieve)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(reverse("renew-subscription"), {
        "plan_id": plan.id,
        "payment_intent_id": "pi_pending",
        "months": 1,
        "auto_renew": False,
    })

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data.get("error") == "Authentication still pending"


@pytest.mark.django_db
def test_renew_subscription_auto_renew_returns_requires_action(monkeypatch):
    user, tenant = _make_tenant_user("auto3ds")
    plan, _ = SubscriptionPlan.objects.get_or_create(
        name="basic", defaults={"price": 10, "duration_month": 1}
    )
    if not plan.stripe_price_id:
        plan.stripe_price_id = "price_test_123"
        plan.save(update_fields=["stripe_price_id"])

    def fake_customer_create(**kwargs):
        return FakeStripeObject(id="cus_auto")

    def fake_customer_retrieve(customer_id):
        return FakeStripeObject(id=customer_id)

    def fake_payment_method_attach(payment_method_id, customer):
        return FakeStripeObject(id=payment_method_id)

    def fake_customer_modify(customer_id, **kwargs):
        return FakeStripeObject(id=customer_id)

    def fake_subscription_create(**kwargs):
        payment_intent = FakeStripeObject(
            id="pi_auto", status="requires_action", client_secret="cs_auto"
        )
        latest_invoice = FakeStripeObject(payment_intent=payment_intent)
        return FakeStripeObject(id="sub_auto", status="incomplete", latest_invoice=latest_invoice)

    monkeypatch.setattr(subscription_views.stripe.Customer, "create", fake_customer_create)
    monkeypatch.setattr(subscription_views.stripe.Customer, "retrieve", fake_customer_retrieve)
    monkeypatch.setattr(subscription_views.stripe.PaymentMethod, "attach", fake_payment_method_attach)
    monkeypatch.setattr(subscription_views.stripe.Customer, "modify", fake_customer_modify)
    monkeypatch.setattr(subscription_views.stripe.Subscription, "create", fake_subscription_create)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(reverse("renew-subscription"), {
        "plan_id": plan.id,
        "payment_method_id": "pm_auto_123",
        "months": 1,
        "auto_renew": True,
    })

    assert response.status_code == 200
    assert response.data.get("requires_action") is True
    assert response.data.get("auto_renew") is True


@pytest.mark.django_db
def test_user_subscription_change_plan_allows_unlimited_target_plan():
    user, tenant = _make_tenant_user("unlimited-user-sub")
    premium_plan = SubscriptionPlan.objects.create(
        name="premium",
        price=80,
        duration_month=12,
        max_employees=0,
    )
    subscription = UserSubscription.objects.create(user=user, plan=premium_plan)

    for idx in range(3):
        employee_user = User.objects.create_user(
            email=f"employee_unlimited_{idx}@test.com",
            password="pass",
            full_name=f"Employee {idx}",
            tenant=tenant,
            role="Client-Staff",
        )
        assert Employee.objects.filter(user=employee_user, tenant=tenant, is_active=True).exists()

    subscription.change_plan(premium_plan)
    subscription.refresh_from_db()

    assert subscription.plan == premium_plan


@pytest.mark.django_db
def test_user_subscription_change_plan_from_unlimited_to_finite_validates_employee_count():
    user, tenant = _make_tenant_user("finite-user-sub")
    unlimited_plan = SubscriptionPlan.objects.create(
        name="premium",
        price=80,
        duration_month=12,
        max_employees=0,
    )
    limited_plan = SubscriptionPlan.objects.create(
        name="enterprise",
        price=120,
        duration_month=12,
        max_employees=2,
    )
    subscription = UserSubscription.objects.create(user=user, plan=unlimited_plan)

    for idx in range(3):
        employee_user = User.objects.create_user(
            email=f"employee_finite_{idx}@test.com",
            password="pass",
            full_name=f"Employee {idx}",
            tenant=tenant,
            role="Client-Staff",
        )
        assert Employee.objects.filter(user=employee_user, tenant=tenant, is_active=True).exists()

    with pytest.raises(ValidationError, match="No puede cambiar a este plan"):
        subscription.change_plan(limited_plan)


@pytest.mark.django_db
def test_subscription_change_plan_from_unlimited_to_finite_validates_employee_count():
    user, tenant = _make_tenant_user("finite-tenant-sub")
    unlimited_plan = SubscriptionPlan.objects.create(
        name="premium",
        price=80,
        duration_month=12,
        max_employees=0,
    )
    limited_plan = SubscriptionPlan.objects.create(
        name="enterprise",
        price=120,
        duration_month=12,
        max_employees=2,
    )
    subscription = Subscription.objects.create(tenant=tenant, plan=unlimited_plan, is_active=True)

    for idx in range(3):
        employee_user = User.objects.create_user(
            email=f"employee_tenant_{idx}@test.com",
            password="pass",
            full_name=f"Employee {idx}",
            tenant=tenant,
            role="Client-Staff",
        )
        assert Employee.objects.filter(user=employee_user, tenant=tenant, is_active=True).exists()

    with pytest.raises(ValidationError, match="No puede cambiar a este plan"):
        subscription.change_plan(limited_plan)


@pytest.mark.django_db
def test_limit_helpers_treat_zero_as_unlimited():
    user, tenant = _make_tenant_user("limit-helpers")
    tenant.max_employees = 0
    tenant.max_users = 0

    assert can_add_employee(tenant, count=500, current_count=999)
    assert can_add_user(tenant, count=500, current_count=999)


@pytest.mark.django_db
def test_tenant_has_feature_reads_settings_snapshot_safely():
    user, tenant = _make_tenant_user("tenant-feature")
    plan = tenant.subscription_plan
    plan.features = {"appointments": True}
    plan.save(update_fields=["features"])

    tenant.settings["plan_features"] = {"appointments": True}
    tenant.save(update_fields=["settings"])

    assert tenant_has_feature(tenant, "appointments") is True
    assert tenant_has_feature(tenant, "cash_register") is False


@pytest.mark.django_db
def test_access_control_has_feature_returns_false_for_missing_key():
    user, tenant = _make_tenant_user("access-feature")
    tenant.settings["plan_features"] = {"appointments": True}
    tenant.save(update_fields=["settings"])

    assert has_feature(tenant, "appointments") is True
    assert has_feature(tenant, "custom_branding") is False


@pytest.mark.django_db
def test_sync_plan_consistency_command_dry_run_does_not_persist():
    user, tenant = _make_tenant_user("sync-dry-run")
    plan = tenant.subscription_plan
    plan.features = {"appointments": True}
    plan.save(update_fields=["features"])

    tenant.settings["plan_features"] = {"appointments": True}
    tenant.max_employees = 999
    tenant.max_users = 999
    tenant.save(update_fields=["settings", "max_employees", "max_users"])

    stdout = StringIO()
    call_command("sync_plan_consistency", stdout=stdout)

    plan.refresh_from_db()
    tenant.refresh_from_db()

    assert "cash_register" not in plan.features
    assert tenant.max_employees == 999
    assert tenant.max_users == 999
    assert "DRY-RUN" in stdout.getvalue()


@pytest.mark.django_db
def test_sync_plan_consistency_command_apply_normalizes_and_syncs():
    user, tenant = _make_tenant_user("sync-apply")
    other_plan = SubscriptionPlan.objects.create(
        name="premium",
        price=80,
        duration_month=12,
        max_employees=0,
        max_users=0,
        features={"appointments": True, "cash_register": True, "custom_branding": True},
    )

    plan = tenant.subscription_plan
    plan.features = {"appointments": True}
    plan.max_employees = 8
    plan.max_users = 16
    plan.save(update_fields=["features", "max_employees", "max_users"])

    tenant.settings["plan_features"] = {"appointments": True}
    tenant.max_employees = 999
    tenant.max_users = 777
    tenant.save(update_fields=["settings", "max_employees", "max_users"])

    stdout = StringIO()
    call_command(
        "sync_plan_consistency",
        "--apply",
        "--apply-feature-values",
        "--apply-limits",
        stdout=stdout,
    )

    plan.refresh_from_db()
    tenant.refresh_from_db()

    assert plan.features["cash_register"] is False
    assert tenant.settings["plan_features"]["cash_register"] is False
    assert tenant.max_employees == plan.max_employees
    assert tenant.max_users == plan.max_users
    assert "Summary" in stdout.getvalue()
