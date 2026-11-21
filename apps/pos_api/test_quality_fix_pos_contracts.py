"""Regresiones CR-08, CR-12 y CR-13 del backend POS."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import RequestFactory, override_settings
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.auth_api.models import User
from apps.pos_api.models import CashCount, CashRegister, Receipt, Sale
from apps.pos_api.views import CashRegisterViewSet, SaleViewSet
from apps.subscriptions_api.models import SubscriptionPlan
from apps.tenants_api.models import Tenant

_PRINT_SECRET = 'quality-fix-print-secret-with-enough-entropy-1234567890'


class _PrintRequest:
    user = type('_User', (), {'id': 1, 'tenant': None})()
    tenant = None


def _setup_tenant():
    plan = SubscriptionPlan.objects.get_or_create(
        name='qf-pos-plan',
        defaults={'price': 0, 'is_active': True, 'is_public': True,
                  'features': {'cash_register': True, 'pos': True}},
    )[0]
    tenant = Tenant.objects.create(
        name='POS QF', subdomain='posqf', subscription_plan=plan, is_active=True
    )
    user = User.objects.create_superuser(
        email='posqf@test.com', password='p', full_name='POS QF', tenant=tenant
    )
    return tenant, user


def _view(view_class, request, action, **kwargs):
    if not isinstance(request, Request):
        original = request
        request = Request(original)
        request.user = getattr(original, 'user', None)
        request.tenant = getattr(original, 'tenant', None)
    view = view_class()
    view.request = request
    view.action = action
    view.kwargs = kwargs
    view.format_kwarg = None
    return view


# ── CR-08 ───────────────────────────────────────────────────────────────────

@override_settings(AURON_PRINT_JWT_SECRET=_PRINT_SECRET)
def test_quality_fix_cr08_ws_endpoint_keeps_historical_default():
    response = SaleViewSet().print_token(_PrintRequest())
    assert response.data['ws_endpoint'] == 'ws://localhost:8081/ws'


@override_settings(
    AURON_PRINT_JWT_SECRET=_PRINT_SECRET,
    AURON_PRINT_AGENT_WS_ENDPOINT='',
    AURON_PRINT_AGENT_HOST='127.0.0.1',
    AURON_PRINT_AGENT_WS_PORT=8082,
    AURON_PRINT_AGENT_WS_PATH='/ws',
)
def test_quality_fix_cr08_ws_endpoint_uses_configured_port():
    response = SaleViewSet().print_token(_PrintRequest())
    assert response.data['ws_endpoint'] == 'ws://127.0.0.1:8082/ws'


@override_settings(
    AURON_PRINT_JWT_SECRET=_PRINT_SECRET,
    AURON_PRINT_AGENT_WS_ENDPOINT='ws://printer.local:9090/ws',
)
def test_quality_fix_cr08_explicit_endpoint_wins():
    response = SaleViewSet().print_token(_PrintRequest())
    assert response.data['ws_endpoint'] == 'ws://printer.local:9090/ws'


# ── CR-12 ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_quality_fix_cr12_invalid_count_rolls_back_previous_cash_counts():
    tenant, user = _setup_tenant()
    register = CashRegister.objects.create(
        tenant=tenant, user=user, initial_cash=Decimal('100.00'), is_open=True
    )
    existing = CashCount.objects.create(
        cash_register=register, denomination=Decimal('10.00'), count=2,
        total=Decimal('20.00'),
    )

    factory = APIRequestFactory()
    request = factory.post('/api/pos/cashregisters/{}/cash_count/'.format(register.pk))
    request.data = {
        'counts': [
            {'denomination': '5.00', 'quantity': 3},
            {'denomination': 'no-es-decimal', 'quantity': 1},
        ],
    }
    request.tenant = tenant
    request.user = user
    view = _view(CashRegisterViewSet, request, 'cash_count', pk=str(register.pk))

    response = view.cash_count(request, pk=str(register.pk))

    assert response.status_code == 400
    assert CashCount.objects.filter(cash_register=register).count() == 1
    existing.refresh_from_db()
    assert existing.count == 2
    assert existing.total == Decimal('20.00')


@pytest.mark.django_db
def test_quality_fix_cr12_valid_count_replaces_previous_atomically():
    tenant, user = _setup_tenant()
    register = CashRegister.objects.create(
        tenant=tenant, user=user, initial_cash=Decimal('100.00'), is_open=True
    )
    CashCount.objects.create(
        cash_register=register, denomination=Decimal('10.00'), count=2,
        total=Decimal('20.00'),
    )

    factory = APIRequestFactory()
    request = factory.post('/api/pos/cashregisters/{}/cash_count/'.format(register.pk))
    request.data = {
        'counts': [
            {'denomination': '5.00', 'quantity': 3},
            {'denomination': '20.00', 'count': 1},
        ],
    }
    request.tenant = tenant
    request.user = user
    view = _view(CashRegisterViewSet, request, 'cash_count', pk=str(register.pk))

    response = view.cash_count(request, pk=str(register.pk))

    assert response.status_code == 200
    assert response.data['total_counted'] == Decimal('35.00')
    counts = CashCount.objects.filter(cash_register=register)
    assert counts.count() == 2
    assert {c.denomination for c in counts} == {Decimal('5.00'), Decimal('20.00')}


@pytest.mark.django_db
def test_quality_fix_cr12_duplicate_denominations_do_not_delete_previous_counts():
    tenant, user = _setup_tenant()
    register = CashRegister.objects.create(
        tenant=tenant, user=user, initial_cash=Decimal('0.00'), is_open=True
    )
    existing = CashCount.objects.create(
        cash_register=register, denomination=Decimal('1.00'), count=7,
        total=Decimal('7.00'),
    )

    request = APIRequestFactory().post('/cash_count/')
    request.data = {
        'counts': [
            {'denomination': '5.00', 'quantity': 1},
            {'denomination': '5.00', 'quantity': 2},
        ],
    }
    request.tenant = tenant
    request.user = user
    view = _view(CashRegisterViewSet, request, 'cash_count', pk=str(register.pk))

    response = view.cash_count(request, pk=str(register.pk))

    assert response.status_code == 400
    assert CashCount.objects.filter(cash_register=register).count() == 1
    existing.refresh_from_db()
    assert existing.count == 7


# ── CR-13 ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_quality_fix_cr13_get_print_receipt_has_no_side_effects():
    tenant, user = _setup_tenant()
    sale = Sale.objects.create(tenant=tenant, user=user, total=Decimal('10.00'))
    request = Request(RequestFactory().get('/api/pos/sales/{}/print_receipt/'.format(sale.pk)))
    request.tenant = tenant
    request.user = user
    view = _view(SaleViewSet, request, 'print_receipt', pk=str(sale.pk))

    response = view.print_receipt(request, pk=str(sale.pk))

    assert response.status_code == 200
    assert response.data['receipt']['printed_count'] == 0
    assert not Receipt.objects.filter(sale=sale).exists()


@pytest.mark.django_db
def test_quality_fix_cr13_post_print_receipt_is_the_explicit_write():
    tenant, user = _setup_tenant()
    sale = Sale.objects.create(tenant=tenant, user=user, total=Decimal('10.00'))
    request = Request(APIRequestFactory().post('/api/pos/sales/{}/print_receipt/'.format(sale.pk)))
    request.tenant = tenant
    request.user = user
    view = _view(SaleViewSet, request, 'print_receipt', pk=str(sale.pk))

    response = view.print_receipt(request, pk=str(sale.pk))

    assert response.status_code == 200
    receipt = Receipt.objects.get(sale=sale)
    assert receipt.printed_count == 1
    assert receipt.last_printed is not None


@pytest.mark.django_db
def test_quality_fix_cr13_get_current_does_not_close_stale_register():
    tenant, user = _setup_tenant()
    register = CashRegister.objects.create(
        tenant=tenant, user=user, initial_cash=Decimal('50.00'), is_open=True
    )
    CashRegister.objects.filter(pk=register.pk).update(
        opened_at=timezone.now() - timedelta(days=2)
    )

    request = Request(APIRequestFactory().get('/api/pos/cashregisters/current/'))
    request.tenant = tenant
    request.user = user
    view = _view(CashRegisterViewSet, request, 'current')

    response = view.current(request)

    assert response.status_code == 200
    register.refresh_from_db()
    assert register.is_open is True


@pytest.mark.django_db
def test_quality_fix_cr13_post_current_closes_stale_register():
    tenant, user = _setup_tenant()
    register = CashRegister.objects.create(
        tenant=tenant, user=user, initial_cash=Decimal('50.00'), is_open=True
    )
    CashRegister.objects.filter(pk=register.pk).update(
        opened_at=timezone.now() - timedelta(days=2)
    )

    request = Request(APIRequestFactory().post('/api/pos/cashregisters/current/'))
    request.tenant = tenant
    request.user = user
    view = _view(CashRegisterViewSet, request, 'current')

    response = view.current(request)

    assert response.status_code == 200
    register.refresh_from_db()
    assert register.is_open is False
    assert register.closed_at is not None
