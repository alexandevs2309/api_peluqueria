"""Regresión: el login debe resolver credenciales con bypass RLS explícito.

Con PostgreSQL y RLS activo, ``tenants_api_tenant`` está en fail-closed hasta
que existe un tenant autenticado. Las consultas de login (que corren antes del
JWT) deben envolverse en ``rls_bypass()``; si no, ``select_related('tenant')``
devuelve ``tenant=None`` y la API responde «Usuario sin tenant asignado».

La suite corre sobre SQLite (donde el bypass es no-op), así que estas pruebas
verifican que el contexto se activa, no el aislamiento en sí.
"""
from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.auth_api.serializers import LoginSerializer, RegisterSerializer
from apps.auth_api.utils import resolve_login_user
from apps.tenants_api.models import Tenant


class TestLoginUsesRlsBypass(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="RLS Login Tenant",
            subdomain="rls-login",
            is_active=True,
        )
        self.user = get_user_model().objects.create_user(
            email="rls-login@example.test",
            password="clave-de-prueba",
            tenant=self.tenant,
        )

    def test_login_with_explicit_subdomain_enters_bypass(self):
        serializer = LoginSerializer(data={
            "email": self.user.email,
            "password": "clave-de-prueba",
            "tenant_subdomain": self.tenant.subdomain,
        })
        with patch("apps.auth_api.serializers.rls_bypass") as bypass:
            self.assertTrue(serializer.is_valid(), serializer.errors)
        bypass.assert_called_once_with()
        self.assertEqual(serializer.validated_data["tenant"].pk, self.tenant.pk)

    def test_login_without_subdomain_enters_bypass(self):
        serializer = LoginSerializer(data={
            "email": self.user.email,
            "password": "clave-de-prueba",
        })
        with patch("apps.auth_api.serializers.rls_bypass") as bypass:
            self.assertTrue(serializer.is_valid(), serializer.errors)
        bypass.assert_called_once_with()
        self.assertEqual(serializer.validated_data["tenant"].pk, self.tenant.pk)

    def test_resolve_login_user_enters_bypass(self):
        with patch("apps.auth_api.utils.rls_bypass") as bypass:
            found = resolve_login_user(self.user.email, self.tenant.subdomain)
        bypass.assert_called_once_with()
        self.assertEqual(found.pk, self.user.pk)

    def test_registration_enters_bypass_for_tenant_lookup(self):
        serializer = RegisterSerializer(data={
            "email": "nuevo-rls@example.test",
            "full_name": "Nuevo RLS",
            "password": "clave-de-prueba",
            "tenant_subdomain": self.tenant.subdomain,
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # La creación del usuario tiene un CHECK preexistente que exige tenant
        # o superuser; se mockea para aislar solo la resolución del tenant.
        with (
            patch("apps.auth_api.serializers.rls_bypass") as bypass,
            patch.object(get_user_model().objects, "create_user", return_value=self.user),
        ):
            serializer.save()
        bypass.assert_called_once_with()
        self.assertEqual(self.user.tenant_id, self.tenant.pk)
