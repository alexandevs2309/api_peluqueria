import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APIClient

from apps.roles_api.default_permissions import ensure_role_default_permissions
from apps.roles_api.models import Role, UserRole
from apps.subscriptions_api.models import SubscriptionPlan
from apps.subscriptions_api.plan_consistency import build_plan_settings_snapshot, tenant_has_feature
from apps.tenants_api.models import Tenant


User = get_user_model()


@pytest.fixture
def default_plans(db):
    call_command("create_default_plans", verbosity=0)
    return list(SubscriptionPlan.objects.order_by("name"))


def _make_client_admin_for_plan(plan, suffix):
    bootstrap_owner = User.objects.create_superuser(
        email=f"bootstrap-{suffix}@example.com",
        password="pass1234",
        full_name=f"Bootstrap {suffix}",
    )
    tenant = Tenant.objects.create(
        name=f"Tenant {suffix}",
        subdomain=f"tenant-{suffix}",
        owner=bootstrap_owner,
        subscription_plan=plan,
        plan_type=plan.name,
        max_employees=plan.max_employees,
        max_users=plan.max_users,
        settings=build_plan_settings_snapshot(plan),
    )
    owner = User.objects.create_user(
        email=f"owner-{suffix}@example.com",
        password="pass1234",
        full_name=f"Owner {suffix}",
        tenant=tenant,
        role="Client-Admin",
        business_role="owner",
    )
    tenant.owner = owner
    tenant.save(update_fields=["owner"])

    role, _ = Role.objects.get_or_create(
        name="Client-Admin",
        defaults={"scope": "TENANT", "description": "Administrador de peluqueria"},
    )
    ensure_role_default_permissions(role)
    UserRole.objects.get_or_create(user=owner, tenant=tenant, role=role)
    return owner, tenant


@pytest.mark.django_db
def test_default_plans_that_advertise_cash_register_grant_the_feature(default_plans):
    plans_with_cash_register = [plan for plan in default_plans if plan.features.get("cash_register")]

    assert plans_with_cash_register, "Default plans must include at least one cash-register-capable plan"
    assert "standard" in {plan.name for plan in plans_with_cash_register}, "Plan Pro must include cash_register"

    for plan in plans_with_cash_register:
        _, tenant = _make_client_admin_for_plan(plan, f"feature-{plan.name}")
        assert tenant_has_feature(tenant, "cash_register") is True


@pytest.mark.django_db
def test_client_admin_can_open_cash_register_for_every_cash_register_plan(default_plans):
    cash_register_plans = [plan for plan in default_plans if plan.features.get("cash_register")]

    for plan in cash_register_plans:
        user, _ = _make_client_admin_for_plan(plan, f"cash-{plan.name}")
        client = APIClient()
        client.force_authenticate(user=user)

        list_response = client.get("/api/pos/cashregisters/")
        assert list_response.status_code == status.HTTP_200_OK, (
            f"{plan.name} Client-Admin should list cash registers, got {list_response.status_code}: "
            f"{getattr(list_response, 'data', None)}"
        )

        create_response = client.post("/api/pos/cashregisters/", {"initial_cash": "1000.00"}, format="json")
        assert create_response.status_code == status.HTTP_201_CREATED, (
            f"{plan.name} Client-Admin should open cash register, got {create_response.status_code}: "
            f"{getattr(create_response, 'data', None)}"
        )
