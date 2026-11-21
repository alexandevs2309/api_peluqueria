#!/usr/bin/env python
"""Verificación de Celery worker real con rol de BD no propietario (Fase E.2).

Requiere un worker separado ejecutándose con las mismas variables de entorno::

    DJANGO_SETTINGS_MODULE=backend.rls_test_settings \
    AURON_RLS_DB_NAME=auron_rls_test AURON_RLS_DB_USER=auron_api \
    AURON_RLS_DB_PORT=55434 \
    python -m celery -A backend worker -l warning -n rls_probe@%h

La prueba encola ``auto_close_old_cash_registers`` (marcada con
``@internal_task``) sin ningún contexto tenant en el productor. Si el worker
no aplicara el bypass controlado, FORCE RLS haría que la tarea no viera filas y
el resultado sería ``Closed 0 old cash registers``.
"""
from __future__ import annotations

import os
import sys
import time
from datetime import timedelta
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.rls_test_settings")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import django  # noqa: E402

django.setup()

from apps.core.tenant_rls import clear_tenant_context, rls_bypass  # noqa: E402
from apps.pos_api.models import CashRegister  # noqa: E402
from apps.pos_api.tasks import auto_close_old_cash_registers  # noqa: E402
from apps.tenants_api.models import Tenant  # noqa: E402
from django.utils import timezone  # noqa: E402


def main() -> int:
    print("=== Celery worker RLS verification (rol no propietario) ===", flush=True)
    from apps.auth_api.models import User

    with rls_bypass():
        tenant = Tenant.objects.create(
            name="RLS Worker Tenant", subdomain="rls_worker_tenant", is_active=True
        )
        user = User.objects.create(
            email="rls_worker@example.test", password="x",
            full_name="RLS Worker", tenant=tenant,
        )
        register = CashRegister.objects.create(tenant=tenant, user=user, is_open=True)
        # opened_at es auto_now_add: hay que forzarlo con UPDATE para simular
        # una caja abierta de días anteriores.
        CashRegister.objects.filter(pk=register.pk).update(
            opened_at=timezone.now() - timedelta(days=5)
        )
        register_id = register.pk
        old_count = CashRegister.objects.filter(
            pk=register.pk, is_open=True, opened_at__date__lt=timezone.localdate()
        ).count()
        print(f"seeded_old_registers={old_count}", flush=True)
    clear_tenant_context()

    # El productor no fija ningún GUC: el worker debe abrir su propio bypass.
    async_result = auto_close_old_cash_registers.delay()
    deadline = time.monotonic() + 45
    result = None
    while time.monotonic() < deadline:
        if async_result.state in {"SUCCESS", "FAILURE"}:
            result = async_result.result
            break
        time.sleep(0.5)

    ok = result == "Closed 1 old cash registers"
    print(f"worker_result={result!r}", flush=True)
    with rls_bypass():
        register.refresh_from_db()
        closed = not register.is_open
        CashRegister.objects.filter(pk=register_id).delete()
        User.objects.filter(pk=user.pk).delete()
        Tenant.objects.filter(pk=tenant.pk).delete()
    print(f"register_closed={closed}", flush=True)
    print("RESULT: " + ("PASS" if ok and closed else "FAIL"), flush=True)
    return 0 if ok and closed else 1


if __name__ == "__main__":
    sys.exit(main())
