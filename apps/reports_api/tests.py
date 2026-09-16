import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status


@pytest.fixture
def admin_user(db, django_user_model):
    user = django_user_model.objects.create_superuser(
        email="admin@example.com",
        password="password123",
        is_staff=True,
        is_active=True,
    )
    return user


@pytest.fixture
def reports_user(db):
    """Usuario con permisos de reportes y plan con features reports/export_reports."""
    from django.contrib.auth.models import Permission
    from apps.roles_api.models import Role, UserRole
    from apps.subscriptions_api.models import SubscriptionPlan
    from apps.auth_api.factories import UserFactory

    plan, _ = SubscriptionPlan.objects.get_or_create(
        name="report-test-plan",
        defaults={
            "price": 0,
            "duration_month": 1,
            "max_employees": 5,
            "features": {"reports": True, "export_reports": True},
        },
    )
    if plan.features != {"reports": True, "export_reports": True}:
        plan.features = {"reports": True, "export_reports": True}
        plan.save(update_fields=["features"])

    role, _ = Role.objects.get_or_create(name="a_report_test_role")
    perms = Permission.objects.filter(
        content_type__app_label="reports_api",
        codename__in=["view_sales_reports", "view_employee_reports", "view_kpi_dashboard"],
    )
    role.permissions.add(*perms)

    user = UserFactory(is_email_verified=True)
    UserRole.objects.create(user=user, role=role, tenant=user.tenant)
    user.tenant.subscription_plan = plan
    user.tenant.save(update_fields=["subscription_plan"])

    client = APIClient()
    client.force_authenticate(user=user)
    return user, client


@pytest.mark.django_db
def test_sales_report(reports_user):
    _, client = reports_user
    response = client.get(reverse("sales-report"))
    assert response.status_code == status.HTTP_200_OK
    assert "total_sales" in response.data
    assert "monthly_sales" in response.data
    assert "sales_by_day" in response.data
    assert "top_services" in response.data


@pytest.mark.django_db
def test_appointments_report(reports_user):
    _, client = reports_user
    now = timezone.now()
    response = client.get(
        reverse("calendar-data"),
        {"start": (now - __import__('datetime').timedelta(days=30)).isoformat(), "end": now.isoformat()},
    )
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.data, list)


@pytest.mark.django_db
def test_employee_performance_report(reports_user):
    _, client = reports_user
    response = client.get(reverse("employee-report"))
    assert response.status_code == status.HTTP_200_OK
    assert "total_employees" in response.data


@pytest.mark.django_db
def test_report_export_invalid_format(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    url = reverse("export-report") + "?type=invalid"
    response = client.get(url)
    assert response.status_code == status.HTTP_400_BAD_REQUEST