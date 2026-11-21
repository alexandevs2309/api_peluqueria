"""Regresiones de seguridad: BE-02, BE-03, BE-04, BE-10 y CR-15 (backend)."""

from types import SimpleNamespace
from unittest.mock import patch

import json

import pytest
from django.core.cache import cache
from django.test import RequestFactory
from rest_framework.exceptions import ValidationError

from apps.subscriptions_api.middleware import (
    APIRateLimitMiddleware,
    SubscriptionValidationMiddleware,
)
from apps.subscriptions_api.plan_consistency import tenant_has_feature
from apps.subscriptions_api.registration_views import register_with_plan
from apps.subscriptions_api.validators import SubscriptionLimitValidator
from rest_framework.test import APIRequestFactory


@pytest.mark.parametrize(
    'plan_name, expected_limit',
    [
        ('pro', 150000),       # legacy R1 conserva límites de Premium
        ('enterprise', None),  # único plan ilimitado
        ('pro_old', 10000),    # desconocido -> basic
        ('', 10000),           # sin plan -> basic
    ],
)
def test_sec_fix_be02_unknown_plan_falls_back_to_basic(plan_name, expected_limit):
    cache.clear()
    request = RequestFactory().get('/api/clients/clients/')
    request.user = SimpleNamespace(
        is_authenticated=True, is_superuser=False, id=1, tenant=None,
    )
    request.tenant = SimpleNamespace(
        id=77, subscription_plan=SimpleNamespace(name=plan_name),
    )

    middleware = APIRateLimitMiddleware(lambda _r: None)
    assert middleware.process_request(request) is None

    if expected_limit is None:
        assert not hasattr(request, 'rate_limit_limit')
    else:
        assert request.rate_limit_limit == expected_limit


def test_sec_fix_be03_downgrade_revokes_premium_features():
    premium = SimpleNamespace(name='premium', features={
        'appointments': True, 'cash_register': True, 'payroll': True,
        'advanced_reports': True,
    })
    basic = SimpleNamespace(name='basic', features={
        'appointments': True, 'cash_register': True,
    })
    tenant = SimpleNamespace(
        id=1,
        name='tenant-downgrade',
        subscription_plan=premium,
        plan_type='premium',
        settings={'plan_features': {
            'appointments': True,
            'payroll': True,
            'advanced_reports': True,
        }},
    )

    assert tenant_has_feature(tenant, 'payroll') is True

    tenant.subscription_plan = basic  # plan_type queda stale a propósito
    assert tenant_has_feature(tenant, 'payroll') is False
    assert tenant_has_feature(tenant, 'advanced_reports') is False
    assert tenant_has_feature(tenant, 'appointments') is True


@pytest.mark.parametrize('status_value', ['past_due', 'suspended'])
def test_sec_fix_be04_limited_subscription_blocks_business_write(status_value):
    cache.clear()
    tenant = SimpleNamespace(
        id=91,
        subscription_status=status_value,
        is_active=False,
        subscription_plan=SimpleNamespace(name='basic'),
    )
    request = RequestFactory().post('/api/clients/clients/')
    request.user = SimpleNamespace(
        is_authenticated=True, is_superuser=False, id=5, tenant=tenant,
    )
    request.tenant = tenant

    with patch('apps.subscriptions_api.middleware.sync_subscription_state'):
        response = SubscriptionValidationMiddleware(lambda _r: None).process_request(request)

    assert response.status_code == 402
    payload = json.loads(response.content)
    assert payload['code'] == 'PAYMENT_REQUIRED'
    assert payload['subscription_status'] == status_value
    assert request.subscription_limited is True


def test_sec_fix_be10_legacy_superadmin_role_does_not_bypass_limits():
    tenant = SimpleNamespace(id=3)
    user = SimpleNamespace(
        is_superuser=False, role='SuperAdmin', tenant=tenant,
    )

    with patch('apps.subscriptions_api.validators.get_user_active_subscription', return_value=None), \
            patch('apps.employees_api.models.Employee.objects.filter') as employee_filter:
        employee_filter.return_value.count.return_value = 999
        with pytest.raises(ValidationError):
            SubscriptionLimitValidator.validate_employee_limit(user, tenant)


@pytest.mark.django_db
def test_sec_fix_cr15_register_with_plan_rejects_non_public_plan():
    from apps.subscriptions_api.models import SubscriptionPlan
    from apps.tenants_api.models import Tenant

    SubscriptionPlan.objects.create(
        name='enterprise', price=999, duration_month=12,
        is_active=True, is_public=False,
    )
    request = APIRequestFactory().post('/api/subscriptions/register-with-plan/', {
        'fullName': 'Owner Test',
        'email': 'cr15-non-public@example.com',
        'businessName': 'Negocio CR15',
        'planType': 'enterprise',
    }, format='json')

    response = register_with_plan(request)

    assert response.status_code == 400
    assert response.data['code'] == 'INVALID_PLAN'
    assert not Tenant.objects.filter(name='Negocio CR15').exists()
