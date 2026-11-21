"""Regresiones de seguridad: BE-04 y BE-10 en TenantMiddleware."""

import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.test import RequestFactory
from django.utils import timezone

from apps.tenants_api.middleware import TenantMiddleware
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan


def test_sec_fix_be10_middleware_ignores_legacy_superadmin_role():
    middleware = TenantMiddleware(lambda _r: None)

    legacy_role = SimpleNamespace(is_authenticated=True, is_superuser=False, role='SuperAdmin')
    real_superuser = SimpleNamespace(is_authenticated=True, is_superuser=True, role='Client-Admin')
    anonymous = SimpleNamespace(is_authenticated=False, is_superuser=False, role='SuperAdmin')

    assert middleware._is_superadmin(legacy_role) is False
    assert middleware._is_superadmin(real_superuser) is True
    assert middleware._is_superadmin(anonymous) is False


@pytest.mark.django_db
@pytest.mark.parametrize('status_value', ['past_due', 'suspended'])
def test_sec_fix_be04_limited_tenant_write_returns_402(status_value):
    past = timezone.now() - timedelta(days=1)
    plan = SubscriptionPlan.objects.create(
        name=f'sec-fix-{status_value}', price=10, duration_month=1,
        is_active=True, is_public=True,
    )
    tenant = Tenant.objects.create(
        name=f'Tenant {status_value}',
        subdomain=f'sec-fix-{status_value}',
        subscription_plan=plan,
        subscription_status=status_value,
        is_active=False,
        access_until=past,
        billing_info={
            'past_due_since': past.isoformat(),
            'suspended_at': past.isoformat(),
        },
    )
    User = Tenant.owner.field.related_model
    user = User.objects.create_user(
        email=f'sec-fix-{status_value}@example.com',
        password='pass',
        full_name='Sec Fix User',
        tenant=tenant,
    )

    request = RequestFactory().post('/api/clients/clients/')
    request.user = user

    # Tenant.save() fuerza 'trial' en la creación: se ajusta el estado con UPDATE.
    Tenant.objects.filter(pk=tenant.pk).update(
        subscription_status=status_value, is_active=False,
    )
    tenant.refresh_from_db()

    with patch('apps.tenants_api.middleware.sync_subscription_state'):
        response = TenantMiddleware(lambda _r: None).process_request(request)

    assert response.status_code == 402
    payload = json.loads(response.content)
    assert payload['code'] == 'PAYMENT_REQUIRED'
    assert payload['subscription_status'] == status_value
    assert request.subscription_limited is True


@pytest.mark.django_db
def test_sec_fix_be04_renewal_path_remains_available_for_limited_tenant():
    past = timezone.now() - timedelta(days=1)
    plan = SubscriptionPlan.objects.create(
        name='sec-fix-renew', price=10, duration_month=1,
        is_active=True, is_public=True,
    )
    tenant = Tenant.objects.create(
        name='Tenant renew',
        subdomain='sec-fix-renew',
        subscription_plan=plan,
        subscription_status='suspended',
        is_active=False,
        access_until=past,
        billing_info={'suspended_at': past.isoformat()},
    )
    User = Tenant.owner.field.related_model
    user = User.objects.create_user(
        email='sec-fix-renew@example.com',
        password='pass',
        full_name='Sec Fix Renew',
        tenant=tenant,
    )

    Tenant.objects.filter(pk=tenant.pk).update(
        subscription_status='suspended', is_active=False,
    )
    tenant.refresh_from_db()

    request = RequestFactory().post('/api/subscriptions/renew/')
    request.user = user

    with patch('apps.tenants_api.middleware.sync_subscription_state'):
        assert TenantMiddleware(lambda _r: None).process_request(request) is None
