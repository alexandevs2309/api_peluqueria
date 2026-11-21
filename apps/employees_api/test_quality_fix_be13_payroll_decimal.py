"""BE-13: importes de nómina serializados con precisión Decimal (nunca float)."""
from datetime import date
from decimal import Decimal

import pytest
from django.test import RequestFactory
from rest_framework.renderers import JSONRenderer
from rest_framework.request import Request

from apps.auth_api.models import User
from apps.employees_api.earnings_models import RegaliaPascual
from apps.employees_api.earnings_views import PayrollViewSet, _money_str
from apps.employees_api.models import Employee
from apps.subscriptions_api.models import SubscriptionPlan
from apps.tenants_api.models import Tenant


def test_quality_fix_be13_money_str_preserves_exact_decimal():
    assert _money_str(Decimal('0.10')) == '0.10'
    assert _money_str(Decimal('999999999999.99')) == '999999999999.99'
    # Un float redondearía este valor; str(Decimal) no debe hacerlo.
    assert _money_str(Decimal('1.005')) == '1.005'
    assert _money_str(None) == '0'


@pytest.mark.django_db
def test_quality_fix_be13_regalia_response_has_exact_string_amounts():
    plan = SubscriptionPlan.objects.create(name='be13-plan', price=0, is_active=True, is_public=True)
    tenant = Tenant.objects.create(
        name='BE13', subdomain='be13', subscription_plan=plan, is_active=True
    )
    user = User.objects.create_user(
        email='be13@test.com', password='p', full_name='BE13 User',
        tenant=tenant, is_email_verified=True,
    )
    employee = Employee.objects.create(
        user=user, tenant=tenant, payment_type='fixed',
        fixed_salary=Decimal('1000.00'), is_active=True, hire_date=date(2024, 1, 1),
    )
    RegaliaPascual.objects.create(
        tenant=tenant, employee=employee, year=2025,
        ordinary_salary_annual=Decimal('1234567890.12'),
        amount=Decimal('0.10'),
    )

    view = PayrollViewSet()
    request = Request(RequestFactory().get('/api/payroll/client/payroll/regalia/'))
    request.tenant = tenant
    request.user = user

    response = view.list_regalia(request)
    row = response.data['regalias'][0]

    assert isinstance(row['ordinary_salary_annual'], str)
    assert row['ordinary_salary_annual'] == '1234567890.12'
    assert isinstance(row['amount'], str)
    assert row['amount'] == '0.10'

    rendered = JSONRenderer().render(response.data)
    assert b'"amount":"0.10"' in rendered
