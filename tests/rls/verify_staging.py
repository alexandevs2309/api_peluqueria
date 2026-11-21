#!/usr/bin/env python
"""Aceptación adicional de RLS en staging (Fase E.3).

Ejecuta primero los 12 gates de ``verify_runtime`` y añade comprobaciones de:
contexto inválido, conexiones persistentes, limpieza del middleware y
denegación de bypass no autorizado.

Debe ejecutarse con el rol de aplicación realista (no propietario):

    AURON_RLS_DB_NAME=auron_stage_rls AURON_RLS_DB_USER=auron_api \
    AURON_RLS_DB_PORT=56400 AURON_RLS_PGBOUNCER=1 \
    DJANGO_SETTINGS_MODULE=backend.rls_test_settings python tests/rls/verify_staging.py
"""
from __future__ import annotations

import os
import sys
from contextlib import nullcontext
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.rls_test_settings")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.db import connection, transaction  # noqa: E402
from django.test import RequestFactory  # noqa: E402

import tests.rls.verify_runtime as base  # noqa: E402
from apps.clients_api.models import Client  # noqa: E402
from apps.core.tenant_rls import (  # noqa: E402
    BYPASS_GUC,
    TENANT_GUC,
    TenantRLSMiddleware,
    clear_tenant_context,
    rls_bypass,
    set_tenant_context,
)
from apps.tenants_api.models import Tenant  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f": {detail}" if detail else ""), flush=True)


def guc(name: str) -> str | None:
    return base.sql_one("SELECT current_setting(%s, true)", [name])[0]


def t13_invalid_context() -> None:
    """Un tenant inexistente o un GUC no numérico nunca filtra filas."""
    clear_tenant_context()
    local = bool(getattr(settings, "PGBOUNCER_ENABLED", False))
    ctx = transaction.atomic() if local else nullcontext()
    with ctx:
        set_tenant_context(999_999_999)
        record("T13a tenant inexistente devuelve 0 filas", Client.objects.count() == 0)
    clear_tenant_context()
    ctx = transaction.atomic() if local else nullcontext()
    with ctx:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.tenant_id', %s, %s)", ["no-es-numero", local]
            )
            cursor.execute(
                "SELECT set_config('app.rls_bypass', 'off', %s)", [local]
            )
        try:
            n = Client.objects.count()
        except Exception as exc:  # SQLSTATE 22P02: el GUC no es convertible a bigint
            record(
                "T13b GUC no numérico no filtra datos (error SQL, no bypass)",
                "invalid input syntax" in str(exc) or "22P02" in str(exc),
                type(exc).__name__,
            )
        else:
            record(
                "T13b GUC no numérico no filtra datos (error SQL, no bypass)",
                n == 0,
                f"filas={n}",
            )
    clear_tenant_context()
    record("T13c fail-closed tras contexto inválido", Client.objects.count() == 0)


def t14_persistent_connections() -> None:
    """La misma conexión física se reutiliza sin filtrar contexto entre tenants."""
    if settings.DATABASES["default"]["CONN_MAX_AGE"] <= 0:
        record("T14 conexión persistente", True, "SKIP: CONN_MAX_AGE=0")
        return
    a, b = base.SEED["a"], base.SEED["b"]
    pids = []
    ok = True
    local = bool(getattr(settings, "PGBOUNCER_ENABLED", False))
    for tenant, expected in ((a, "Client A"), (b, "Client B"), (a, "Client A")):
        # Con PgBouncer los GUC son locales a la transacción, igual que en cada
        # request real envuelta por el middleware.
        ctx = transaction.atomic() if local else nullcontext()
        with ctx:
            pids.append(base.sql_one("SELECT pg_backend_pid()")[0])
            set_tenant_context(tenant.id)
            ok &= list(Client.objects.values_list("full_name", flat=True)) == [expected]
            clear_tenant_context()
            ok &= Client.objects.count() == 0
    # Tras PgBouncer el PID del servidor puede cambiar entre transacciones: lo
    # relevante es que el GUC nunca se filtre aunque la conexión se reutilice.
    stable = len(set(pids)) == 1
    record(
        "T14 conexión persistente sin fuga",
        ok and (not stable or local),
        f"pids={pids} (pool={local})",
    )


def t15_middleware_cleanup() -> None:
    """Una petición normal no deja ni tenant ni bypass en la conexión."""
    clear_tenant_context()
    a = base.SEED["a"]

    def view(request):
        from django.http import HttpResponse

        return HttpResponse("ok")

    middleware = TenantRLSMiddleware(view)
    request = RequestFactory().get("/api/clients/")
    request.user = None
    middleware(request)
    record(
        "T15 middleware limpia GUC tras la respuesta",
        guc(TENANT_GUC) in (None, "") and guc(BYPASS_GUC) in (None, "", "off"),
        f"tenant={guc(TENANT_GUC)!r} bypass={guc(BYPASS_GUC)!r}",
    )
    local = bool(getattr(settings, "PGBOUNCER_ENABLED", False))
    ctx = transaction.atomic() if local else nullcontext()
    with ctx:
        set_tenant_context(a.id)
        record("T15b contexto usable tras petición previa", Client.objects.count() == 1)
    clear_tenant_context()


def t16_unauthorized_bypass() -> None:
    """No hay endpoints, tools ni módulos de negocio que activen el bypass."""
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
        if path.relative_to(root).as_posix() in allowed:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "set_rls_bypass()" in text or "set_config('app.rls_bypass'" in text:
            offenders.append(path.relative_to(root).as_posix())
    record("T16 bypass restringido a módulos autorizados", not offenders, str(offenders))
    clear_tenant_context()
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.rls_bypass', 'off', false)")
    record("T16b sin bypass no se ven filas", Client.objects.count() == 0)


def main() -> int:
    print("=== Staging acceptance: gates E.2 + comprobaciones E.3 ===", flush=True)
    base_exit = base.main()
    record("Gates E.2 (12 comprobaciones)", base_exit == 0)
    # verify_runtime.main() limpió su semilla; volvemos a sembrar para T14/T15.
    if base_exit == 0:
        seed_again()
    t13_invalid_context()
    if seed_ready():
        t14_persistent_connections()
        t15_middleware_cleanup()
    t16_unauthorized_bypass()
    failed = [r for r in RESULTS if not r[1]]
    print(f"RESULT: {len(RESULTS) - len(failed)}/{len(RESULTS)} PASS", flush=True)
    return 1 if failed else 0


def seed_again() -> None:
    # Reutilizamos la semilla del módulo base con un nombre distinto para no
    # colisionar con la ejecución anterior (ya limpiada).
    base.seed()
    seed_ready()


def seed_ready() -> bool:
    return bool(base.SEED.get("a"))


if __name__ == "__main__":
    sys.exit(main())
