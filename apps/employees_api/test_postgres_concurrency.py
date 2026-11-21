"""
V-01 — Concurrencia REAL de liquidaciones/nómina (BE-01) sobre PostgreSQL.

Estas pruebas sólo tienen sentido con un servidor PostgreSQL: `select_for_update()`
es un no-op en SQLite. Se ejecutan con `DJANGO_SETTINGS_MODULE=pgtest_settings`
(apuntando a una BD efímera) y se omiten explícitamente con cualquier otro motor.

Cubre: dos peticiones simultáneas, clave distinta e igual, exclusión mientras
otro hilo mantiene el lock, reintento tras la liberación y recuperación de un
fallo `IntegrityError` con rollback.
"""
import threading
import time
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction

from apps.auth_api.models import User
from apps.employees_api.earnings_models import AlreadyPaidError, RegaliaPascual
from apps.employees_api.models import Employee
from apps.subscriptions_api.models import SubscriptionPlan
from apps.tenants_api.models import Tenant

pytestmark = pytest.mark.django_db(transaction=True)


def _require_postgres():
    if connection.vendor != 'postgresql':
        pytest.skip('V-01 exige PostgreSQL real; select_for_update() es no-op en SQLite')


def _fixture(prefix):
    plan = SubscriptionPlan.objects.create(name=f'p-{prefix}', price=10, is_active=True, is_public=True)
    tenant = Tenant.objects.create(name='T', subdomain=prefix, subscription_plan=plan, is_active=True)
    admin = User.objects.create_superuser(
        email=f'{prefix}@test.com', password='p', full_name='Admin', tenant=tenant
    )
    emp = Employee.objects.create(
        user=admin, tenant=tenant, payment_type='fixed',
        fixed_salary=Decimal('50000.00'), is_active=True,
    )
    regalia = RegaliaPascual.objects.create(
        employee=emp, tenant=tenant, year=2026,
        ordinary_salary_annual=Decimal('600000.00'), amount=Decimal('50000.00'),
        status='calculated',
    )
    return tenant, admin, regalia


def _pay_in_thread(regalia_id, user_id, reference, key, barrier, results):
    """Cada hilo abre su propia conexión y lee ANTES de la barrera."""
    connection.close()
    try:
        regalia = RegaliaPascual.objects.get(pk=regalia_id)
        user = User.objects.get(pk=user_id)
        barrier.wait(timeout=10)
        regalia.mark_as_paid(user, reference, idempotency_key=key)
        results.append(('ok', reference))
    except AlreadyPaidError as exc:
        results.append(('already_paid', str(exc)))
    except IntegrityError as exc:
        results.append(('integrity_error', str(exc)))
    except Exception as exc:  # se registra para no ocultar fallos inesperados
        results.append(('unexpected', f'{type(exc).__name__}: {exc}'))
    finally:
        connection.close()


def _run_two(args_a, args_b):
    results = []
    barrier = threading.Barrier(2)
    threads = [
        threading.Thread(target=_pay_in_thread, args=(*a, barrier, results))
        for a in (args_a, args_b)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
        assert not t.is_alive(), 'un hilo quedó bloqueado: no hay exclusión efectiva'
    return results


def test_two_concurrent_requests_different_keys_only_one_payment():
    _require_postgres()
    tenant, admin, regalia = _fixture('v01diff')
    rid, uid = regalia.pk, admin.pk

    results = _run_two((rid, uid, 'REF-A', 'key-a'), (rid, uid, 'REF-B', 'key-b'))

    statuses = sorted(r[0] for r in results)
    assert statuses == ['already_paid', 'ok'], results
    regalia.refresh_from_db()
    assert regalia.status == 'paid'
    assert regalia.payment_reference in ('REF-A', 'REF-B')
    assert RegaliaPascual.objects.filter(pk=rid, status='paid').count() == 1


def _install_update_audit():
    """Trigger de prueba que cuenta UPDATEs que cambian el estado financiero."""
    table = RegaliaPascual._meta.db_table
    with connection.cursor() as cur:
        cur.execute('DROP TABLE IF EXISTS v01_update_audit')
        cur.execute('CREATE TABLE v01_update_audit (new_ref text, old_status text, new_status text)')
        cur.execute(
            'CREATE OR REPLACE FUNCTION v01_audit_fn() RETURNS trigger AS $fn$ '
            'BEGIN '
            '  IF OLD.status IS DISTINCT FROM NEW.status '
            '     OR OLD.payment_reference IS DISTINCT FROM NEW.payment_reference THEN '
            '    INSERT INTO v01_update_audit(new_ref, old_status, new_status) '
            '    VALUES (NEW.payment_reference, OLD.status, NEW.status); '
            '  END IF; '
            '  RETURN NEW; '
            'END; $fn$ LANGUAGE plpgsql'
        )
        cur.execute(f'DROP TRIGGER IF EXISTS v01_audit_trg ON {table}')
        cur.execute(
            f'CREATE TRIGGER v01_audit_trg AFTER UPDATE ON {table} '
            'FOR EACH ROW EXECUTE FUNCTION v01_audit_fn()'
        )


def _read_update_audit():
    with connection.cursor() as cur:
        cur.execute('SELECT new_ref, old_status, new_status FROM v01_update_audit ORDER BY 1')
        return cur.fetchall()


def test_two_concurrent_requests_same_key_produce_one_effect():
    _require_postgres()
    tenant, admin, regalia = _fixture('v01same')
    rid, uid = regalia.pk, admin.pk
    _install_update_audit()

    try:
        results = _run_two((rid, uid, 'REF-S', 'shared-key'), (rid, uid, 'REF-S2', 'shared-key'))

        # Con la misma clave el replay es idempotente: ambos pueden responder ok,
        # pero el trigger debe registrar UNA SOLA transición a paid.
        assert all(r[0] in ('ok', 'already_paid') for r in results), results
        regalia.refresh_from_db()
        assert regalia.status == 'paid'
        assert regalia.payment_reference in ('REF-S', 'REF-S2')
        assert regalia.idempotency_key == 'shared-key'

        audited = _read_update_audit()
        assert len(audited) == 1, f'hubo {len(audited)} afectaciones financieras: {audited}'
        assert audited[0][0] == regalia.payment_reference, audited
        assert audited[0][1] == 'calculated' and audited[0][2] == 'paid', audited
    finally:
        with connection.cursor() as cur:
            cur.execute(f'DROP TRIGGER IF EXISTS v01_audit_trg ON {RegaliaPascual._meta.db_table}')
            cur.execute('DROP TABLE IF EXISTS v01_update_audit')


def test_lock_is_exclusive_until_commit_then_loser_sees_paid():
    _require_postgres()
    tenant, admin, regalia = _fixture('v01lock')
    rid, uid = regalia.pk, admin.pk

    holder_done = threading.Event()
    holder_started = threading.Event()

    def holder():
        connection.close()
        try:
            with transaction.atomic():
                locked = RegaliaPascual.objects.select_for_update().get(pk=rid)
                holder_started.set()
                time.sleep(1.5)  # mantiene el lock durante el intento rival
                assert locked.status == 'calculated'
        finally:
            connection.close()
            holder_done.set()

    def contender():
        connection.close()
        try:
            obj = RegaliaPascual.objects.get(pk=rid)
            obj.mark_as_paid(User.objects.get(pk=uid), 'REF-H', idempotency_key='key-h')
            results.append('ok')
        except AlreadyPaidError:
            results.append('already_paid')
        except Exception as exc:
            results.append(f'unexpected:{type(exc).__name__}:{exc}')
        finally:
            connection.close()

    results = []
    t_holder = threading.Thread(target=holder)
    t_contender = threading.Thread(target=contender)
    t_holder.start()
    assert holder_started.wait(timeout=10), 'el holder no adquirió el lock'
    t_contender.start()

    # Mientras el holder no libera, el contendor NO puede haber pagado.
    time.sleep(0.4)
    assert not results, 'el segundo pago ocurrió mientras otro hilo tenía FOR UPDATE'
    RegaliaPascual.objects.filter(pk=rid).update(status='paid')  # efecto externo simulado
    t_holder.join(timeout=10)
    t_contender.join(timeout=20)
    assert not t_contender.is_alive(), 'el contendor quedó bloqueado tras liberar el lock'

    regalia.refresh_from_db()
    assert regalia.status == 'paid'
    assert RegaliaPascual.objects.filter(pk=rid, status='paid').count() == 1


def test_integrity_error_rolls_back_and_retry_succeeds():
    _require_postgres()
    tenant, admin, first = _fixture('v01rb1')
    second = RegaliaPascual.objects.create(
        employee=first.employee, tenant=tenant, year=2027,
        amount=Decimal('10.00'), status='calculated',
    )

    first.mark_as_paid(admin, 'REF-1', idempotency_key='shared-unique-key')
    first.refresh_from_db()
    assert first.status == 'paid'

    # Misma clave en OTRA obligación del mismo tenant: la constraint única falla.
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            second.mark_as_paid(admin, 'REF-2', idempotency_key='shared-unique-key')
    second.refresh_from_db()
    assert second.status == 'calculated', 'el fallo no hizo rollback de la afectación'
    assert second.payment_reference is None

    # Reintento con clave nueva: paga una sola vez.
    second.mark_as_paid(admin, 'REF-3', idempotency_key='fresh-key')
    second.refresh_from_db()
    assert second.status == 'paid'
    assert second.payment_reference == 'REF-3'
    assert RegaliaPascual.objects.filter(tenant=tenant, idempotency_key='shared-unique-key').count() == 1


def test_concurrent_http_posts_return_one_200_and_one_409():
    _require_postgres()
    tenant, admin, regalia = _fixture('v01http')
    rid, uid = regalia.pk, admin.pk
    results = []

    def post(reference, key, barrier):
        connection.close()
        from rest_framework.parsers import JSONParser
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory
        from apps.employees_api.earnings_views import PayrollViewSet

        raw = APIRequestFactory().post(
            f'/api/employees/client/payroll/regalia/{rid}/pay',
            {'reference': reference, 'idempotency_key': key}, format='json',
        )
        request = Request(raw, parsers=[JSONParser()])
        request.user = User.objects.get(pk=uid)
        request.tenant = Tenant.objects.get(pk=tenant.pk)
        barrier.wait(timeout=10)
        try:
            response = PayrollViewSet().pay_regalia(request, regalia_id=str(rid))
            results.append(response.status_code)
        except Exception as exc:
            results.append(f'exception:{type(exc).__name__}')
        finally:
            connection.close()

    barrier = threading.Barrier(2)
    threads = [
        threading.Thread(target=post, args=('HTTP-A', 'hk-a', barrier)),
        threading.Thread(target=post, args=('HTTP-B', 'hk-b', barrier)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
        assert not t.is_alive(), 'una petición HTTP quedó bloqueada'

    assert sorted(results) == [200, 409], results
    regalia.refresh_from_db()
    assert RegaliaPascual.objects.filter(pk=rid, status='paid').count() == 1
