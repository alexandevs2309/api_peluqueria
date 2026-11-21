#!/usr/bin/env python
"""Verificación de management commands con rol de BD no propietario (Fase E.2).

Ejecuta ``close_old_registers`` (hereda ``RLSInternalCommand``) sin contexto
tenant. Sin el bypass controlado, FORCE RLS haría que el comando viera 0 tenants
y 0 cajas; con él, debe cerrar la caja sembrada.
"""
from __future__ import annotations

import os
import sys
from datetime import timedelta
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.rls_test_settings")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import django  # noqa: E402

django.setup()

from django.core.management import call_command  # noqa: E402
from django.utils import timezone  # noqa: E402

from apps.auth_api.models import User  # noqa: E402
from apps.core.tenant_rls import clear_tenant_context, rls_bypass  # noqa: E402
from apps.pos_api.models import CashRegister  # noqa: E402
from apps.tenants_api.models import Tenant  # noqa: E402


def main() -> int:
    print("=== Management command RLS verification (rol no propietario) ===", flush=True)
    with rls_bypass():
        Tenant.objects.filter(subdomain="rls_command_tenant").delete()
        tenant = Tenant.objects.create(
            name="RLS Command Tenant", subdomain="rls_command_tenant", is_active=True
        )
        user = User.objects.create(
            email="rls_command@example.test", password="x",
            full_name="RLS Command", tenant=tenant,
        )
        register = CashRegister.objects.create(tenant=tenant, user=user, is_open=True)
        CashRegister.objects.filter(pk=register.pk).update(
            opened_at=timezone.now() - timedelta(days=5)
        )
        register_id = register.pk
    clear_tenant_context()

    call_command("close_old_registers")

    with rls_bypass():
        register.refresh_from_db()
        closed = not register.is_open
        CashRegister.objects.filter(pk=register_id).delete()
        User.objects.filter(pk=user.pk).delete()
        Tenant.objects.filter(pk=tenant.pk).delete()
    print(f"register_closed={closed}", flush=True)
    print("RESULT: " + ("PASS" if closed else "FAIL"), flush=True)
    return 0 if closed else 1


if __name__ == "__main__":
    sys.exit(main())
