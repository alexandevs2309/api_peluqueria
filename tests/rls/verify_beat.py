#!/usr/bin/env python
"""Verificación de Celery Beat real con rol de BD no propietario (Fase E.3).

Requiere:
  * un worker con ``backend.rls_test_settings`` y el rol de aplicación;
  * un beat con ``backend.rls_beat_settings`` (schedule de 1 segundo).

El productor siembra una caja antigua bajo bypass y luego limpia el contexto.
Beat debe encolar la tarea interna y el worker debe cerrarla sin que el
productor fije ningún GUC.
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

from apps.auth_api.models import User  # noqa: E402
from apps.core.tenant_rls import clear_tenant_context, rls_bypass  # noqa: E402
from apps.pos_api.models import CashRegister  # noqa: E402
from apps.tenants_api.models import Tenant  # noqa: E402
from django.utils import timezone  # noqa: E402


def main() -> int:
    print("=== Celery beat RLS verification (rol no propietario) ===", flush=True)
    with rls_bypass():
        tenant = Tenant.objects.create(
            name="RLS Beat Tenant", subdomain="rls_beat_tenant", is_active=True
        )
        user = User.objects.create(
            email="rls_beat@example.test", password="x",
            full_name="RLS Beat", tenant=tenant,
        )
        register = CashRegister.objects.create(tenant=tenant, user=user, is_open=True)
        CashRegister.objects.filter(pk=register.pk).update(
            opened_at=timezone.now() - timedelta(days=5)
        )
        register_id = register.pk
    clear_tenant_context()

    closed = False
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        with rls_bypass():
            closed = not CashRegister.objects.get(pk=register_id).is_open
        if closed:
            break
        time.sleep(0.5)

    with rls_bypass():
        CashRegister.objects.filter(pk=register_id).delete()
        User.objects.filter(pk=user.pk).delete()
        Tenant.objects.filter(pk=tenant.pk).delete()
    print(f"beat_register_closed={closed}", flush=True)
    print("RESULT: " + ("PASS" if closed else "FAIL"), flush=True)
    return 0 if closed else 1


if __name__ == "__main__":
    sys.exit(main())
