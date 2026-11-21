"""Regresiones del endurecimiento RLS en runtime (Fase E.2).

Estas pruebas corren con ``backend.test_settings`` (SQLite) y comprueban la
lógica de bypass controlado y la forma de la migración. El aislamiento real con
rol no propietario se comprueba con PostgreSQL en ``verify_runtime.py``.
"""
from __future__ import annotations

import importlib
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from apps.core import rls_internal, tenant_rls


class TestExplicitBypass(TestCase):
    def test_restores_previous_tenant_context_on_success(self):
        gucs = {"app.tenant_id": "7", "app.rls_bypass": "off"}
        with (
            patch.object(tenant_rls, "_get_guc", side_effect=gucs.get),
            patch.object(tenant_rls, "set_rls_bypass") as bypass_on,
            patch.object(tenant_rls, "set_tenant_context") as set_tenant,
            patch.object(tenant_rls, "clear_tenant_context") as clear,
        ):
            with tenant_rls.rls_bypass():
                pass
        bypass_on.assert_called_once_with()
        set_tenant.assert_called_once_with("7")
        clear.assert_not_called()

    def test_restores_fail_closed_when_no_previous_context(self):
        gucs = {"app.tenant_id": None, "app.rls_bypass": None}
        with (
            patch.object(tenant_rls, "_get_guc", side_effect=gucs.get),
            patch.object(tenant_rls, "set_rls_bypass") as bypass_on,
            patch.object(tenant_rls, "set_tenant_context") as set_tenant,
            patch.object(tenant_rls, "clear_tenant_context") as clear,
        ):
            with tenant_rls.rls_bypass():
                pass
        bypass_on.assert_called_once_with()
        set_tenant.assert_not_called()
        clear.assert_called_once_with()

    def test_restores_context_when_body_raises(self):
        gucs = {"app.tenant_id": "9", "app.rls_bypass": "off"}
        with (
            patch.object(tenant_rls, "_get_guc", side_effect=gucs.get),
            patch.object(tenant_rls, "set_rls_bypass"),
            patch.object(tenant_rls, "set_tenant_context") as set_tenant,
            patch.object(tenant_rls, "clear_tenant_context"),
        ):
            with self.assertRaises(ValueError):
                with tenant_rls.rls_bypass():
                    raise ValueError("boom")
        set_tenant.assert_called_once_with("9")

    def test_booking_resolves_subdomain_under_temporary_bypass(self):
        request = SimpleNamespace(
            path="/api/booking/mi-bar/info", META={}, COOKIES={}, user=None
        )
        tenant = SimpleNamespace(id=42)
        queryset = patch.object(
            tenant_rls, "rls_bypass", return_value=_null_context()
        )
        with (
            queryset as bypass,
            patch("apps.tenants_api.models.Tenant.objects") as objects,
            patch.object(tenant_rls, "set_tenant_context") as set_tenant,
        ):
            objects.filter.return_value.only.return_value.first.return_value = tenant
            tenant_rls._apply(request)
        bypass.assert_called_once_with()
        set_tenant.assert_called_once_with(42)
        objects.filter.assert_called_once_with(subdomain="mi-bar", deleted_at__isnull=True)


class _null_context:
    """Context manager mínimo para sustituir ``rls_bypass`` en pruebas."""

    def __enter__(self):
        return None

    def __exit__(self, *args):
        return False


class TestInternalTaskDecorator(TestCase):
    def test_wrapped_task_runs_under_bypass(self):
        with patch.object(rls_internal, "rls_bypass", return_value=_null_context()) as bypass:

            @rls_internal.internal_task
            def add(a, b):
                return a + b

            self.assertEqual(add(2, 3), 5)
        bypass.assert_called_once_with()

    def test_decorator_preserves_task_name(self):
        @rls_internal.internal_task
        def named_task():
            return None

        self.assertEqual(named_task.__name__, "named_task")


class TestMigrationShape(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.m12 = importlib.import_module("apps.tenants_api.migrations.0012_rls_tenant_isolation")
        cls.m14 = importlib.import_module("apps.tenants_api.migrations.0014_rls_runtime_hardening")

    def test_force_tables_match_0012_exactly(self):
        expected = {*self.m12.TENANT_TABLES, self.m12.TENANT_TABLE}
        self.assertEqual(set(self.m14.FORCE_TABLES), expected)
        self.assertEqual(len(self.m14.FORCE_TABLES), 33)

    def test_forward_sql_has_force_and_three_indirect_policies(self):
        sql = self.m14.FORWARD_SQL
        self.assertEqual(sql.count("FORCE ROW LEVEL SECURITY"), 36)
        for table in ("pos_api_saledetail", "inventory_api_stockmovement", "notifications_api_inappnotification"):
            self.assertIn(f"rls_tenant_indirect_{table}", sql)
            self.assertIn("USING", sql)
            self.assertIn("WITH CHECK", sql)

    def test_reverse_sql_removes_policies_and_force(self):
        sql = self.m14.REVERSE_SQL
        self.assertIn("NO FORCE ROW LEVEL SECURITY", sql)
        self.assertIn("DROP POLICY IF EXISTS rls_tenant_indirect_pos_api_saledetail", sql)
        self.assertIn("ALTER TABLE pos_api_saledetail DISABLE ROW LEVEL SECURITY", sql)

    def test_migration_0012_is_unchanged_in_shape(self):
        self.assertEqual(len(self.m12.TENANT_TABLES), 32)
        self.assertNotIn("FORCE", self.m12.FORWARD_SQL)


class TestAuditOnCommitBypass(TestCase):
    def test_user_creation_audit_uses_explicit_bypass(self):
        audit_signals = importlib.import_module("apps.audit_api.signals")
        user = SimpleNamespace(
            pk=1, email="audit@example.test", role="CLIENT", tenant_id=None,
            tenant=None, refresh_from_db=lambda: None,
        )
        with (
            patch.object(audit_signals, "rls_bypass", return_value=_null_context()) as bypass,
            patch.object(audit_signals, "create_audit_log") as create,
        ):
            audit_signals._audit_user_creation(user)
        bypass.assert_called_once_with()
        create.assert_called_once()
        self.assertEqual(create.call_args.kwargs["user"], None)

    def test_generic_audit_write_uses_explicit_bypass(self):
        audit_signals = importlib.import_module("apps.audit_api.signals")
        with (
            patch.object(audit_signals, "rls_bypass", return_value=_null_context()) as bypass,
            patch.object(audit_signals, "create_audit_log") as create,
        ):
            audit_signals._write_audit_log(action="CREATE")
        bypass.assert_called_once_with()
        create.assert_called_once_with(action="CREATE")
