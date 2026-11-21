#!/usr/bin/env python
"""Verificación RLS contra PostgreSQL con rol NO propietario (Fase E.2).

Requisitos previos:
  * BD migrada con ``backend.rls_test_settings`` usando el rol propietario.
  * Ejecutar este script con ``AURON_RLS_DB_USER=<rol no propietario>``.
  * El rol debe ser NOSUPERUSER y NOBYPASSRLS (se comprueba en T1).

Ejemplo::

    AURON_RLS_DB_NAME=auron_rls_test AURON_RLS_DB_USER=auron_api \
    AURON_RLS_DB_PORT=55434 DJANGO_SETTINGS_MODULE=backend.rls_test_settings \
    python tests/rls/verify_runtime.py

No conecta con producción. Imprime PASS/FAIL por prueba y termina con exit 1 si
alguna falla. Los datos sembrados se eliminan al final con bypass controlado.
"""
from __future__ import annotations

import os
import sys
from datetime import timedelta
from functools import wraps
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.rls_test_settings")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.contenttypes.models import ContentType  # noqa: E402
from django.core.exceptions import PermissionDenied  # noqa: E402
from django.db import connection, transaction  # noqa: E402
from django.db.utils import IntegrityError, ProgrammingError  # noqa: E402
from django.utils import timezone  # noqa: E402

from apps.clients_api.models import Client  # noqa: E402
from apps.core.rls_internal import internal_task  # noqa: E402
from apps.core.tenant_rls import (  # noqa: E402
    _apply,
    clear_tenant_context,
    rls_bypass,
    set_tenant_context,
)
from apps.inventory_api.models import Product, StockMovement  # noqa: E402
from apps.notifications_api.models import InAppNotification  # noqa: E402
from apps.pos_api.models import CashRegister, Sale, SaleDetail  # noqa: E402
from apps.tenants_api.models import Tenant  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []
SEED: dict[str, object] = {}

# psycopg3 reporta la violación de WITH CHECK como ProgrammingError
# (SQLSTATE 42501); Django puede mapearla a PermissionDenied o IntegrityError.
RLS_VIOLATION = (IntegrityError, ProgrammingError, PermissionDenied)
PGB = bool(getattr(settings, "PGBOUNCER_ENABLED", False))


def pgb_atomic(fn):
    """En modo PgBouncer las comprobaciones necesitan una transacción que
    contenga los GUC locales, igual que hace el middleware en cada request."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if PGB:
            with transaction.atomic():
                return fn(*args, **kwargs)
        return fn(*args, **kwargs)

    return wrapper


def check(name: str, fn):
    try:
        result = fn()
    except Exception as exc:  # noqa: BLE001 - queremos ver todas las fallas
        RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
        print(f"FAIL {name}: {type(exc).__name__}: {exc}", flush=True)
    else:
        if result == "SKIP":
            RESULTS.append((name, True, "SKIP"))
            print(f"SKIP {name}", flush=True)
        else:
            RESULTS.append((name, True, ""))
            print(f"PASS {name}", flush=True)


def sql_one(query: str, params: list | None = None):
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        return cursor.fetchone()


def assert_equal(actual, expected, msg: str) -> None:
    if actual != expected:
        raise AssertionError(f"{msg}: esperado {expected!r}, obtenido {actual!r}")


def count(model) -> int:
    return model.objects.count()


# ---------------------------------------------------------------------------
# Semilla (usa exactamente el mecanismo autorizado de la aplicación)
# ---------------------------------------------------------------------------
def seed() -> None:
    SEED.clear()
    from apps.auth_api.models import User

    with rls_bypass():
        # Limpieza defensiva de ejecuciones anteriores que abortaron antes de
        # cleanup(). User.tenant es SET_NULL y existe un CHECK que exige tenant
        # o superuser: hay que borrar primero los usuarios de prueba.
        User.objects.filter(
            email__in=["rls_runtime_a@example.test", "rls_runtime_b@example.test"]
        ).delete()
        Tenant.objects.filter(subdomain__startswith="rls_").delete()
        a = Tenant.objects.create(
            name="RLS Runtime A", subdomain="rls_runtime_a",
            is_active=True, plan_type="", subscription_status="trial",
        )
        b = Tenant.objects.create(
            name="RLS Runtime B", subdomain="rls_runtime_b",
            is_active=True, plan_type="", subscription_status="trial",
        )
        user_a = User.objects.create(
            email="rls_runtime_a@example.test", password="x", full_name="User A", tenant=a
        )
        user_b = User.objects.create(
            email="rls_runtime_b@example.test", password="x", full_name="User B", tenant=b
        )
        client_a = Client.objects.create(tenant=a, full_name="Client A", notes="")
        client_b = Client.objects.create(tenant=b, full_name="Client B", notes="")
        product_a = Product.objects.create(
            tenant=a, name="Product A", sku="RLS-A", price=Decimal("10.00")
        )
        product_b = Product.objects.create(
            tenant=b, name="Product B", sku="RLS-B", price=Decimal("20.00")
        )
        sale_a = Sale.objects.create(tenant=a, user=user_a, total=Decimal("10.00"))
        sale_b = Sale.objects.create(tenant=b, user=user_b, total=Decimal("20.00"))
        ct = ContentType.objects.get_for_model(Product)
        detail_a = SaleDetail.objects.create(
            sale=sale_a, content_type=ct, object_id=product_a.id,
            name="Detail A", quantity=1, price=Decimal("10.00"),
        )
        detail_b = SaleDetail.objects.create(
            sale=sale_b, content_type=ct, object_id=product_b.id,
            name="Detail B", quantity=1, price=Decimal("20.00"),
        )
        move_a = StockMovement.objects.create(product=product_a, quantity=1, reason="rls-test")
        move_b = StockMovement.objects.create(product=product_b, quantity=1, reason="rls-test")
        notif_a = InAppNotification.objects.create(
            recipient=user_a, title="Notif A", message="rls-test"
        )
        notif_b = InAppNotification.objects.create(
            recipient=user_b, title="Notif B", message="rls-test"
        )
        register_a = CashRegister.objects.create(
            tenant=a, user=user_a, is_open=True,
            opened_at=timezone.now() - timedelta(days=5),
        )
    SEED.update(
        a=a, b=b, user_a=user_a, user_b=user_b,
        client_a=client_a, client_b=client_b,
        product_a=product_a, product_b=product_b,
        sale_a=sale_a, sale_b=sale_b,
        detail_a=detail_a, detail_b=detail_b,
        move_a=move_a, move_b=move_b,
        notif_a=notif_a, notif_b=notif_b,
        register_a=register_a,
    )


def cleanup() -> None:
    with rls_bypass():
        for key in ("notif_a", "notif_b", "move_a", "move_b", "detail_a", "detail_b",
                    "register_a", "sale_a", "sale_b", "product_a", "product_b",
                    "client_a", "client_b", "user_a", "user_b", "a", "b"):
            obj = SEED.get(key)
            if obj is not None:
                type(obj).objects.filter(pk=obj.pk).delete()


# ---------------------------------------------------------------------------
# Pruebas
# ---------------------------------------------------------------------------
def t1_identity():
    user, superuser, bypass, owned = sql_one(
        "SELECT current_user, rolsuper, rolbypassrls, "
        "(SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        " WHERE n.nspname='public' AND c.relkind='r' AND pg_get_userbyid(c.relowner)=current_user) "
        "FROM pg_roles WHERE rolname=current_user"
    )
    assert_equal(user, "auron_api", "rol de conexión")
    assert_equal(superuser, False, "rolsuper")
    assert_equal(bypass, False, "rolbypassrls")
    assert_equal(owned, 0, "tablas propiedad del rol de app")


def t2_structure():
    rls, force = sql_one(
        "SELECT count(*) FILTER (WHERE relrowsecurity), "
        "count(*) FILTER (WHERE relforcerowsecurity) "
        "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='public' AND c.relkind='r'"
    )
    assert_equal((rls, force), (36, 36), "tablas RLS/FORCE")
    policies = sql_one("SELECT count(*) FROM pg_policies WHERE schemaname='public'")[0]
    assert_equal(policies, 36, "políticas")
    owned_by_app = sql_one(
        "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='public' AND c.relkind='r' AND c.relrowsecurity "
        "AND pg_get_userbyid(c.relowner) = current_user"
    )[0]
    assert_equal(owned_by_app, 0, "tablas protegidas propiedad del rol de aplicación")


def t3_fail_closed():
    clear_tenant_context()
    for model in (Tenant, Client, Sale, SaleDetail, StockMovement, InAppNotification):
        assert_equal(count(model), 0, f"fail-closed {model._meta.db_table}")
    # La resolución por subdomain sin bypass no debe filtrar nada.
    assert_equal(
        Tenant.objects.filter(subdomain="rls_runtime_a").count(), 0,
        "resolución de subdomain sin contexto",
    )


@pgb_atomic
def t4_tenant_isolation():
    a, b = SEED["a"], SEED["b"]
    for tenant, label, expected in ((a, "A", "Client A"), (b, "B", "Client B")):
        set_tenant_context(tenant.id)
        names = list(Client.objects.values_list("full_name", flat=True))
        assert_equal(names, [expected], f"visibilidad tenant {label}")
        assert_equal(
            Client.objects.filter(tenant_id=b.id if tenant == a else a.id).count(), 0,
            f"lectura cruzada tenant {label}",
        )
        assert_equal(count(Tenant), 1, f"fila Tenant visible para {label}")
    set_tenant_context(a.id)
    other_id = b.id
    with transaction.atomic():
        updated = Client.objects.filter(tenant_id=other_id).update(full_name="HACK")
        assert_equal(updated, 0, "UPDATE cruzado")
    with transaction.atomic():
        deleted = Client.objects.filter(tenant_id=other_id).delete()[0]
        assert_equal(deleted, 0, "DELETE cruzado")
    with transaction.atomic():
        try:
            Client.objects.create(tenant_id=other_id, full_name="HACK", notes="")
        except RLS_VIOLATION:
            pass
        else:
            raise AssertionError("INSERT cruzado permitido por WITH CHECK")
    clear_tenant_context()


@pgb_atomic
def t5_indirect_isolation():
    a, b = SEED["a"], SEED["b"]
    set_tenant_context(a.id)
    assert_equal(
        list(SaleDetail.objects.values_list("name", flat=True)), ["Detail A"],
        "saledetail visibility",
    )
    assert_equal(
        list(StockMovement.objects.values_list("reason", flat=True)), ["rls-test"],
        "stockmovement visibility (1 fila del tenant A)",
    )
    assert_equal(
        list(InAppNotification.objects.values_list("title", flat=True)), ["Notif A"],
        "inappnotification visibility",
    )
    with transaction.atomic():
        assert_equal(
            SaleDetail.objects.filter(sale=SEED["sale_b"]).update(name="HACK"), 0,
            "UPDATE saledetail cruzado",
        )
    with transaction.atomic():
        assert_equal(
            StockMovement.objects.filter(product=SEED["product_b"]).delete()[0], 0,
            "DELETE stockmovement cruzado",
        )
    with transaction.atomic():
        assert_equal(
            InAppNotification.objects.filter(recipient=SEED["user_b"]).update(title="HACK"), 0,
            "UPDATE inappnotification cruzado",
        )
    with transaction.atomic():
        try:
            SaleDetail.objects.create(
                sale=SEED["sale_b"],
                content_type=ContentType.objects.get_for_model(Product),
                object_id=SEED["product_b"].id, name="HACK", quantity=1,
                price=Decimal("1.00"),
            )
        except RLS_VIOLATION:
            pass
        else:
            raise AssertionError("INSERT saledetail cruzado permitido")
    with transaction.atomic():
        try:
            StockMovement.objects.create(product=SEED["product_b"], quantity=1, reason="HACK")
        except RLS_VIOLATION:
            pass
        else:
            raise AssertionError("INSERT stockmovement cruzado permitido")
    clear_tenant_context()


def t6_authorized_bypass():
    with rls_bypass():
        assert_equal(count(Client), 2, "bypass explícito")
        assert_equal(count(Tenant) >= 2, True, "bypass explícito tenants")
    clear_tenant_context()
    assert_equal(count(Client), 0, "restauración fail-closed tras bypass")


def t7_session_guc_cleanup():
    if PGB:
        return "SKIP"
    a = SEED["a"]
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.tenant_id', %s, false)", [str(a.id)])
        cursor.execute("SELECT set_config('app.rls_bypass', 'off', false)")
    assert_equal(count(Client), 1, "GUC de sesión activo")
    clear_tenant_context()
    assert_equal(count(Client), 0, "limpieza de GUC de sesión")
    connection.close()
    assert_equal(count(Client), 0, "conexión reutilizada sin contexto")
    clear_tenant_context()


def t8_transaction_local_guc():
    a = SEED["a"]
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.tenant_id', %s, true)", [str(a.id)])
            cursor.execute("SELECT set_config('app.rls_bypass', 'off', true)")
        assert_equal(count(Client), 1, "GUC local dentro de transacción")
    assert_equal(count(Client), 0, "GUC local expiró al salir de la transacción")
    clear_tenant_context()


@pgb_atomic
def t9_booking_flow():
    a = SEED["a"]
    clear_tenant_context()
    request = SimpleNamespace(
        path="/api/booking/rls_runtime_a/info", META={}, COOKIES={}, user=None
    )
    _apply(request)
    tenant_id = sql_one("SELECT current_setting('app.tenant_id', true)")[0]
    assert_equal(tenant_id, str(a.id), "contexto resuelto por subdomain")
    assert_equal(
        list(Client.objects.values_list("full_name", flat=True)), ["Client A"],
        "booking ve sólo el tenant del subdomain",
    )
    clear_tenant_context()


@pgb_atomic
def t10_registration_flow():
    # Sin contexto, WITH CHECK rechaza el alta de un tenant nuevo. En modo
    # PgBouncer se omite: los signals de auditoría consultan el tenant dentro de
    # la transacción ya iniciada y convierten el error de RLS en un
    # TransactionManagementError. La misma garantía (WITH CHECK) se comprueba
    # en T4 con Client y en tests/rls/verify.sql.
    if not PGB:
        with transaction.atomic():
            try:
                Tenant.objects.create(name="RLS No Bypass", subdomain="rls_no_bypass")
            except RLS_VIOLATION:
                pass
            else:
                raise AssertionError("creación de tenant sin bypass permitida")
    # El flujo real crea el tenant bajo bypass y luego fija contexto.
    with rls_bypass():
        created = Tenant.objects.create(
            name="RLS Runtime C", subdomain="rls_runtime_c", is_active=True
        )
    set_tenant_context(created.id)
    assert_equal(count(Client), 0, "contexto tras crear tenant")
    assert_equal(
        sql_one("SELECT current_setting('app.tenant_id', true)")[0], str(created.id),
        "tenant fijado tras registro",
    )
    SEED["created"] = created
    with rls_bypass():
        created.delete()
    clear_tenant_context()


def t11_internal_task():
    clear_tenant_context()

    @internal_task
    def probe():
        return Tenant.objects.count()

    # Sin bypass, el probe vería 0 filas. El decorador lo autoriza explícitamente.
    assert_equal(probe() >= 2, True, "tarea interna con bypass")
    after = sql_one("SELECT current_setting('app.rls_bypass', true)")[0]
    assert_equal(after or "off", "off", "bypass restaurado tras la tarea")
    clear_tenant_context()


def t12_no_accidental_bypass():
    root = Path(__file__).resolve().parents[1]
    allowed = {
        "apps/core/tenant_rls.py",
        "apps/core/rls_internal.py",
        "apps/auth_api/views.py",
        "apps/subscriptions_api/registration_views.py",
        "apps/audit_api/signals.py",
    }
    offenders = []
    for path in root.rglob("*.py"):
        if ".venv" in path.parts or "migrations" in path.parts or "tests" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        if rel in allowed:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "set_rls_bypass()" in text or "set_config('app.rls_bypass'" in text:
            offenders.append(rel)
    assert_equal(offenders, [], "llamadas de bypass fuera de módulos autorizados")


def main() -> int:
    print("=== RLS runtime verification (rol no propietario) ===", flush=True)
    check("T1 identidad no propietaria", t1_identity)
    seed()
    check("T2 estructura RLS/FORCE/policies", t2_structure)
    check("T3 fallo cerrado sin contexto", t3_fail_closed)
    check("T4 aislamiento entre tenants", t4_tenant_isolation)
    check("T5 relaciones indirectas", t5_indirect_isolation)
    check("T6 bypass autorizado y restauración", t6_authorized_bypass)
    check("T7 GUC de sesión y conexión reutilizada", t7_session_guc_cleanup)
    check("T8 GUC local por transacción", t8_transaction_local_guc)
    check("T9 booking público", t9_booking_flow)
    check("T10 registro de empresas", t10_registration_flow)
    check("T11 tarea interna (Celery)", t11_internal_task)
    check("T12 sin bypass accidental en código", t12_no_accidental_bypass)
    cleanup()
    clear_tenant_context()
    failed = [r for r in RESULTS if not r[1]]
    print(f"RESULT: {len(RESULTS) - len(failed)}/{len(RESULTS)} PASS", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
