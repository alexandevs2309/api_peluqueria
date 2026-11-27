"""Regresiones RLS: el tenant de la sesión no debe depender del tenant de la URL.

En ``/api/booking/<subdomain>/`` el contexto RLS se fija desde el subdomain,
no desde el usuario. Si el visitante tiene cookie de otro negocio, acceder a
``user.tenant`` lanzaba ``Tenant.DoesNotExist`` y convertía la página pública
en un 500.
"""
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from apps.auth_api.authentication import CookieJWTAuthentication, DualJWTAuthentication
from apps.tenants_api.models import Tenant

AUTH_CLASSES = [CookieJWTAuthentication, DualJWTAuthentication]


def _make_tenant(suffix):
    return Tenant.objects.create(
        name=f'RLS Attach {suffix}',
        subdomain=f'rls-attach-{suffix}',
        is_active=True,
        subscription_status='active',
    )


@pytest.mark.django_db
@pytest.mark.parametrize('auth_cls', AUTH_CLASSES)
def test_attach_tenant_resuelve_el_jwt_bajo_bypass_explicito(auth_cls):
    tenant = _make_tenant(auth_cls.__name__.lower())
    state = {'entered': 0, 'bypass': False}

    @contextmanager
    def fake_bypass():
        state['entered'] += 1
        state['bypass'] = True
        try:
            yield
        finally:
            state['bypass'] = False

    class RlsHiddenUser:
        def __init__(self):
            self.is_superuser = False
            self.tenant_id = tenant.id

        @property
        def tenant(self):
            if not state['bypass']:
                raise Tenant.DoesNotExist('RLS oculta el tenant de la petición')
            return tenant

    request = SimpleNamespace()
    with patch('apps.auth_api.authentication.rls_bypass', fake_bypass):
        auth_cls._attach_tenant(request, RlsHiddenUser())

    assert request.tenant == tenant
    assert state['entered'] == 1


@pytest.mark.django_db
@pytest.mark.parametrize('auth_cls', AUTH_CLASSES)
def test_attach_tenant_sin_fila_devuelve_none_en_lugar_de_lanzar(auth_cls):
    state = {'entered': 0, 'bypass': False}

    @contextmanager
    def fake_bypass():
        state['entered'] += 1
        state['bypass'] = True
        try:
            yield
        finally:
            state['bypass'] = False

    class RlsHiddenUser:
        is_superuser = False
        tenant_id = 987654321

        @property
        def tenant(self):
            raise Tenant.DoesNotExist('RLS oculta el tenant de la petición')

    request = SimpleNamespace()
    with patch('apps.auth_api.authentication.rls_bypass', fake_bypass):
        auth_cls._attach_tenant(request, RlsHiddenUser())

    assert request.tenant is None
    assert state['entered'] == 1


@pytest.mark.parametrize('auth_cls', AUTH_CLASSES)
def test_attach_tenant_superuser_no_consulta_tenant(auth_cls):
    class SuperUser:
        is_superuser = True
        tenant_id = 1

        @property
        def tenant(self):
            raise AssertionError('un superusuario no debe consultar tenant')

    request = SimpleNamespace()
    auth_cls._attach_tenant(request, SuperUser())

    assert request.tenant is None
