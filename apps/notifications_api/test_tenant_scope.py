"""Regresiones del foco por tenant en la campana de notificaciones."""
import pytest
from rest_framework.test import APIClient

from apps.auth_api.models import User
from apps.notifications_api.models import InAppNotification
from apps.tenants_api.models import Tenant


@pytest.fixture
def scope_data():
    tenant_a = Tenant.objects.create(name='Alpha', subdomain='alpha-scope', is_active=True)
    tenant_b = Tenant.objects.create(name='Beta', subdomain='beta-scope', is_active=True)
    superuser = User.objects.create_superuser(
        email='root-scope@test.com', password='pass', full_name='Root'
    )
    owned_a = InAppNotification.objects.create(
        recipient=superuser, tenant=tenant_a, type='appointment',
        title='Cita Alpha', message='Cita en Alpha',
    )
    owned_b = InAppNotification.objects.create(
        recipient=superuser, tenant=tenant_b, type='appointment',
        title='Cita Beta', message='Cita en Beta',
    )
    return tenant_a, tenant_b, superuser, owned_a, owned_b


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_superadmin_sin_filtro_ve_todas(scope_data):
    _, _, superuser, _, _ = scope_data
    response = _client(superuser).get('/api/notifications/')
    assert response.status_code == 200
    results = response.data.get('results', response.data)
    assert len(results) == 2


@pytest.mark.django_db
def test_superadmin_con_filtro_solo_ve_ese_tenant(scope_data):
    tenant_a, _, superuser, owned_a, _ = scope_data
    response = _client(superuser).get(f'/api/notifications/?tenant={tenant_a.id}')
    assert response.status_code == 200
    results = response.data.get('results', response.data)
    assert [item['id'] for item in results] == [owned_a.id]
    assert results[0]['tenant'] == tenant_a.id
    assert results[0]['tenant_name'] == 'Alpha'
    assert results[0]['tenant_subdomain'] == 'alpha-scope'


@pytest.mark.django_db
def test_superadmin_con_tenant_inexistente_ve_cero(scope_data):
    _, _, superuser, _, _ = scope_data
    for value in ('999999', 'no-es-un-id'):
        response = _client(superuser).get(f'/api/notifications/?tenant={value}')
        assert response.status_code == 200
        results = response.data.get('results', response.data)
        assert results == []


@pytest.mark.django_db
def test_usuario_de_negocio_ignora_el_parametro_tenant(scope_data):
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    from apps.roles_api.models import Role, UserRole

    tenant_a, _, _, _, _ = scope_data
    user = User.objects.create_user(
        email='staff-scope@test.com', password='pass', full_name='Staff',
        tenant=tenant_a, is_email_verified=True,
    )
    role, _ = Role.objects.get_or_create(name='Client-Admin', defaults={'scope': 'TENANT'})
    content_type = ContentType.objects.get(app_label='notifications_api', model='inappnotification')
    perm, _ = Permission.objects.get_or_create(
        codename='view_inappnotification', content_type=content_type,
        defaults={'name': 'view'},
    )
    role.permissions.add(perm)
    UserRole.objects.get_or_create(user=user, role=role, tenant=tenant_a)

    mine = InAppNotification.objects.create(
        recipient=user, type='system', title='Mía', message='Solo mía'
    )
    response = _client(user).get(f'/api/notifications/?tenant={tenant_a.id + 1}')
    assert response.status_code == 200
    results = response.data.get('results', response.data)
    assert [item['id'] for item in results] == [mine.id]


@pytest.mark.django_db
def test_marcar_todas_leidas_respeta_el_filtro(scope_data):
    tenant_a, _, superuser, owned_a, owned_b = scope_data
    response = _client(superuser).post(f'/api/notifications/mark-all-read/?tenant={tenant_a.id}', {})
    assert response.status_code == 200
    assert response.data['updated'] == 1
    owned_a.refresh_from_db()
    owned_b.refresh_from_db()
    assert owned_a.is_read is True
    assert owned_b.is_read is False


@pytest.mark.django_db
def test_notificacion_hereda_tenant_del_destinatario():
    tenant = Tenant.objects.create(name='Gamma', subdomain='gamma-scope', is_active=True)
    user = User.objects.create_user(
        email='gamma-scope@test.com', password='pass', full_name='Gamma',
        tenant=tenant, is_email_verified=True,
    )
    note = InAppNotification.objects.create(
        recipient=user, type='system', title='Sin tenant explícito', message='Prueba'
    )
    assert note.tenant_id == tenant.id
