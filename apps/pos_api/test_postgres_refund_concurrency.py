"""
V-02 — Reembolsos concurrentes y consistencia (BE-05, BE-07) sobre PostgreSQL.

Complementa al test SQLite `test_refund_tenant_idempotency.py`: aquí la restricción
única `uniq_refund_tenant_idempotency_key` se ejecuta en un motor que la aplica
realmente y dos hilos abren transacciones independientes.

Cubre: repetición secuencial, dos solicitudes concurrentes con la misma clave,
reutilización de clave con payload distinto, reintento tras fallo intermedio y
consistencia entre el registro local (`RefundOperation.result`) y los efectos
(stock + amount_refunded). Se omite si el motor no es PostgreSQL.
"""
import threading
from decimal import Decimal
from unittest import mock

import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import connection

from apps.auth_api.models import User
from apps.inventory_api.models import Product, StockMovement
from apps.pos_api.models import RefundOperation, Sale, SaleDetail
from apps.tenants_api.models import Tenant

pytestmark = pytest.mark.django_db(transaction=True)

REASON = 'Devolución completa por error del cliente'


def _require_postgres():
    if connection.vendor != 'postgresql':
        pytest.skip('V-02 exige PostgreSQL real; los savepoints y UNIQUE se comprueban aquí')


def _fixture(prefix):
    tenant = Tenant.objects.create(name='T', subdomain=prefix, is_active=True)
    admin = User.objects.create_superuser(
        email=f'{prefix}@test.com', password='p', full_name='Admin'
    )
    seller = User.objects.create_user(
        email=f'{prefix}-seller@test.com', password='p', full_name='Seller', tenant=tenant
    )
    product = Product.objects.create(
        tenant=tenant, name='Shampoo', price=Decimal('100'), stock=10
    )
    sale = Sale.objects.create(
        tenant=tenant, total=Decimal('200'), status='confirmed',
        user=seller, created_by=seller,
    )
    ct = ContentType.objects.get(app_label='inventory_api', model='product')
    SaleDetail.objects.create(
        sale=sale, content_type=ct, object_id=product.pk,
        name='Shampoo', quantity=2, price=Decimal('100'),
    )
    return tenant, admin, seller, product, sale


def _call_refund(pk, user_id, tenant_id, key, amount=None, barrier=None, results=None):
    """Ejecuta el action `refund` con una request DRF y su propia conexión."""
    from rest_framework.parsers import JSONParser
    from rest_framework.request import Request
    from rest_framework.test import APIRequestFactory
    from apps.pos_api.views import SaleViewSet

    connection.close()
    payload = {'reason': REASON, 'idempotency_key': key}
    if amount is not None:
        payload['amount'] = str(amount)
    try:
        raw = APIRequestFactory().post(f'/api/pos/sales/{pk}/refund/', payload, format='json')
        request = Request(raw, parsers=[JSONParser()])
        request.user = User.objects.get(pk=user_id)
        request.tenant = Tenant.objects.get(pk=tenant_id) if tenant_id else None
        if barrier:
            barrier.wait(timeout=10)
        response = SaleViewSet().refund(request, pk=str(pk))
        if results is not None:
            results.append((response.status_code, dict(response.data)))
    except Exception as exc:
        if results is not None:
            results.append(('EXC', f'{type(exc).__name__}: {exc}'))
    finally:
        connection.close()


def _run_two(pk, user_id, tenant_id, key_a, key_b, amount_a=None, amount_b=None):
    results = []
    barrier = threading.Barrier(2)
    threads = [
        threading.Thread(target=_call_refund, args=(pk, user_id, tenant_id, key, amt, barrier, results))
        for key, amt in ((key_a, amount_a), (key_b, amount_b))
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
        assert not t.is_alive(), 'un reembolso quedó bloqueado'
    return results


def _state(product, sale, tenant):
    product.refresh_from_db()
    sale.refresh_from_db()
    return {
        'stock': product.stock,
        'refunded': sale.amount_refunded,
        'operations': RefundOperation.objects.filter(tenant=tenant).count(),
        'movements': StockMovement.objects.filter(
            reason__contains=f'venta #{sale.pk}'
        ).count(),
    }


def test_sequential_replay_with_same_key_applies_once():
    _require_postgres()
    tenant, admin, seller, product, sale = _fixture('v02seq')
    tid = tenant.pk
    results = []

    _call_refund(sale.pk, admin.pk, tid, 'seq-key', results=results)
    first_state = _state(product, sale, tenant)
    _call_refund(sale.pk, admin.pk, tid, 'seq-key', results=results)

    assert results[0][0] == 200, results
    assert results[1][0] == 200 and results[1][1].get('idempotent') is True, results
    assert _state(product, sale, tenant) == first_state
    assert first_state['stock'] == 12 and first_state['refunded'] == Decimal('200.00')
    assert first_state['operations'] == 1 and first_state['movements'] == 1


def test_two_concurrent_refunds_same_key_produce_one_effect():
    _require_postgres()
    tenant, admin, seller, product, sale = _fixture('v02conc')
    tid = tenant.pk

    results = _run_two(sale.pk, admin.pk, tid, 'conc-key', 'conc-key')
    codes = sorted(r[0] for r in results)
    assert codes == [200, 200], results  # el replay responde 200 con idempotent=True
    assert sum(1 for r in results if r[1].get('idempotent')) == 1, results

    state = _state(product, sale, tenant)
    assert state['stock'] == 12, state
    assert state['refunded'] == Decimal('200.00'), state
    assert state['operations'] == 1, state
    assert state['movements'] == 1, state

    operation = RefundOperation.objects.get(tenant=tenant, idempotency_key='conc-key')
    assert operation.result, 'el registro de idempotencia no persiste el resultado'
    assert Decimal(operation.result['refunded_amount']) == state['refunded']


def test_key_reuse_with_different_payload_returns_original_without_new_effect():
    _require_postgres()
    tenant, admin, seller, product, sale = _fixture('v02payload')
    tid = tenant.pk
    results = []

    _call_refund(sale.pk, admin.pk, tid, 'same-key', amount=Decimal('50'), results=results)
    _call_refund(sale.pk, admin.pk, tid, 'same-key', amount=Decimal('150'), results=results)

    assert results[0][0] == 200 and results[1][0] == 200, results
    assert results[1][1].get('idempotent') is True
    assert results[1][1].get('refunded_amount') == '50.00', 'El replay devolvió el payload nuevo'
    state = _state(product, sale, tenant)
    assert state['refunded'] == Decimal('50.00'), state
    assert state['operations'] == 1, state
    # 50/200 = 25% de 2 unidades = 0.5 → ROUND_DOWN ⇒ 0; no se repone stock.
    assert state['stock'] == 10 and state['movements'] == 0, state


def test_failure_mid_operation_rolls_back_and_retry_applies_once():
    _require_postgres()
    tenant, admin, seller, product, sale = _fixture('v02fail')
    tid = tenant.pk
    results = []

    # Simula un fallo del proveedor AFTER de iniciar: se produce tras la
    # creación del RefundOperation y antes de completar la reposición/estado.
    original_create = StockMovement.objects.create
    calls = {'n': 0}

    def flaky_create(*args, **kwargs):
        calls['n'] += 1
        if calls['n'] == 1:
            raise RuntimeError('fallo simulado del proveedor de reembolso')
        return original_create(*args, **kwargs)

    with mock.patch.object(StockMovement.objects, 'create', side_effect=flaky_create):
        _call_refund(sale.pk, admin.pk, tid, 'retry-key', results=results)

    assert results[0][0] == 'EXC' and 'fallo simulado' in results[0][1], results
    after_failure = _state(product, sale, tenant)
    assert after_failure['stock'] == 10, after_failure
    assert after_failure['refunded'] == Decimal('0.00'), after_failure
    assert after_failure['operations'] == 0, 'Quedó una operación huérfana sin resultado'
    assert after_failure['movements'] == 0, after_failure

    # Reintento con la misma clave: la operación se crea de nuevo y aplica una sola vez.
    _call_refund(sale.pk, admin.pk, tid, 'retry-key', results=results)
    assert results[1][0] == 200, results
    final_state = _state(product, sale, tenant)
    assert final_state['stock'] == 12, final_state
    assert final_state['refunded'] == Decimal('200.00'), final_state
    assert final_state['operations'] == 1 and final_state['movements'] == 1, final_state
    operation = RefundOperation.objects.get(tenant=tenant, idempotency_key='retry-key')
    assert Decimal(operation.result['refunded_amount']) == Decimal('200.00'), operation.result
