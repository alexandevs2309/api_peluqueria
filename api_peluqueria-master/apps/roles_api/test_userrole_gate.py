"""
FASE 4 Gate Tests — UserRole cross-tenant isolation + anti-escalation.

These tests run BEFORE considering FASE 4 closed.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from apps.auth_api.factories import UserFactory
from apps.roles_api.models import Role, UserRole
from apps.tenants_api.models import Tenant

User = get_user_model()


def _ensure_userrole_perms_on_client_admin():
    """Add userrole permissions to Client-Admin role in test DB."""
    role, _ = Role.objects.get_or_create(name='Client-Admin', defaults={'scope': 'TENANT'})
    for codename in ['add_userrole', 'change_userrole', 'delete_userrole', 'view_userrole']:
        try:
            perm = Permission.objects.get(
                content_type__app_label='roles_api',
                codename=codename,
            )
            role.permissions.add(perm)
        except Permission.DoesNotExist:
            pass


@pytest.fixture
def tenant_a():
    return Tenant.objects.create(name='Tenant A Gate', subdomain='gate-a')


@pytest.fixture
def tenant_b():
    return Tenant.objects.create(name='Tenant B Gate', subdomain='gate-b')


@pytest.fixture
def owner_a(tenant_a):
    _ensure_userrole_perms_on_client_admin()
    user = UserFactory(is_email_verified=True, is_superuser=False, tenant=tenant_a)
    role = Role.objects.get(name='Client-Admin')
    UserRole.objects.get_or_create(user=user, role=role, tenant=tenant_a)
    return user


@pytest.fixture
def owner_b(tenant_b):
    _ensure_userrole_perms_on_client_admin()
    user = UserFactory(is_email_verified=True, is_superuser=False, tenant=tenant_b)
    role = Role.objects.get(name='Client-Admin')
    UserRole.objects.get_or_create(user=user, role=role, tenant=tenant_b)
    return user


@pytest.fixture
def employee_b(tenant_b):
    user = UserFactory(is_email_verified=True, is_superuser=False, tenant=tenant_b)
    role, _ = Role.objects.get_or_create(name='Estilista', defaults={'scope': 'TENANT'})
    UserRole.objects.get_or_create(user=user, role=role, tenant=tenant_b)
    return user


@pytest.mark.django_db
def test_cross_tenant_owner_a_cannot_manage_userrole_of_tenant_b(owner_a, tenant_b):
    """
    GATE TEST 1: Owner de Tenant A no puede crear UserRole para usuarios del Tenant B.
    """
    client = APIClient()
    client.force_authenticate(user=owner_a)

    victim = UserFactory(is_email_verified=True, is_superuser=False, tenant=tenant_b)
    estilista_role, _ = Role.objects.get_or_create(name='Estilista', defaults={'scope': 'TENANT'})

    url = reverse('userrole-list')
    payload = {
        'user': victim.id,
        'role': estilista_role.id,
    }
    response = client.post(url, payload, format='json')

    print(f'Cross-tenant create: {response.status_code} -> {response.data}')
    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN], (
        f"CROSS-TENANT FAILURE: Owner de Tenant A pudo crear UserRole para "
        f"usuario de Tenant B. Response: {response.status_code} {response.data}"
    )


@pytest.mark.django_db
def test_cross_tenant_owner_a_cannot_list_userroles_of_tenant_b(owner_a, tenant_b):
    """
    GATE TEST 1b: Owner de Tenant A no puede ver UserRole de Tenant B.
    """
    victim = UserFactory(is_email_verified=True, is_superuser=False, tenant=tenant_b)
    estilista_role, _ = Role.objects.get_or_create(name='Estilista', defaults={'scope': 'TENANT'})
    UserRole.objects.create(user=victim, role=estilista_role, tenant=tenant_b)

    client = APIClient()
    client.force_authenticate(user=owner_a)
    url = reverse('userrole-list')
    response = client.get(url, format='json')

    print(f'Cross-tenant list: {response.status_code} -> {response.data}')

    if response.status_code == 200:
        userrole_ids = [ur['id'] for ur in response.data]
        victim_ur = UserRole.objects.get(user=victim, tenant=tenant_b)
        assert victim_ur.id not in userrole_ids, (
            f"CROSS-TENANT FAILURE: Owner de Tenant A puede ver UserRole "
            f"id={victim_ur.id} de usuario de Tenant B."
        )


@pytest.mark.django_db
def test_anti_escalation_estilista_cannot_self_assign_admin_role(employee_b):
    """
    GATE TEST 2: Un empleado (Estilista) no puede auto-asignarse
    un rol de admin via el endpoint de UserRole.
    """
    client = APIClient()
    client.force_authenticate(user=employee_b)

    client_admin_role = Role.objects.get(name='Client-Admin')
    url = reverse('userrole-list')
    payload = {
        'user': employee_b.id,
        'role': client_admin_role.id,
    }
    response = client.post(url, payload, format='json')

    print(f'Anti-escalation self-assign: {response.status_code} -> {response.data}')

    assert response.status_code == status.HTTP_403_FORBIDDEN, (
        f"ANTI-ESCALATION FAILURE: Estilista pudo auto-asignarse Client-Admin "
        f"rol. Response: {response.status_code} {response.data}"
    )


@pytest.mark.django_db
def test_estilista_cannot_list_userroles(employee_b):
    """
    GATE TEST 2b: Un empleado sin permisos de gestión no puede listar UserRole.
    """
    client = APIClient()
    client.force_authenticate(user=employee_b)
    url = reverse('userrole-list')
    response = client.get(url, format='json')

    print(f'Estilista list userroles: {response.status_code}')

    assert response.status_code == status.HTTP_403_FORBIDDEN, (
        f"ANTI-ESCALATION FAILURE: Estilista pudo listar UserRoles. "
        f"Response: {response.status_code}"
    )


@pytest.mark.django_db
def test_owner_can_manage_own_tenant_userroles(owner_a, tenant_a):
    """
    SMOKE TEST: Owner A PUEDE gestionar UserRoles de su propio tenant.
    """
    employee = UserFactory(is_email_verified=True, is_superuser=False, tenant=tenant_a)
    estilista_role, _ = Role.objects.get_or_create(name='Estilista', defaults={'scope': 'TENANT'})

    client = APIClient()
    client.force_authenticate(user=owner_a)

    # Create
    url = reverse('userrole-list')
    payload = {'user': employee.id, 'role': estilista_role.id}
    response = client.post(url, payload, format='json')
    print(f'Owner create own tenant: {response.status_code}')
    assert response.status_code == status.HTTP_201_CREATED

    userrole_id = response.data['id']

    # List
    response = client.get(url, format='json')
    print(f'Owner list own tenant: {response.status_code}, count={len(response.data)}')
    assert response.status_code == 200
    assert any(ur['id'] == userrole_id for ur in response.data)

    # Delete
    delete_url = reverse('userrole-detail', kwargs={'pk': userrole_id})
    response = client.delete(delete_url)
    print(f'Owner delete own tenant: {response.status_code}')
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_anti_escalation_owner_cannot_assign_owner_role(owner_a, tenant_a):
    """
    GATE TEST 3: Owner no puede asignar rol 'owner' (restringido por _is_restricted_role).
    """
    employee = UserFactory(is_email_verified=True, is_superuser=False, tenant=tenant_a)

    client = APIClient()
    client.force_authenticate(user=owner_a)

    owner_role = Role.objects.get(name='owner')

    url = reverse('userrole-list')
    payload = {'user': employee.id, 'role': owner_role.id}
    response = client.post(url, payload, format='json')

    print(f'Anti-escalation owner role: {response.status_code} -> {response.data}')
    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"ANTI-ESCALATION FAILURE: Owner pudo asignar rol 'owner' a empleado. "
        f"Response: {response.status_code} {response.data}"
    )
    assert 'role' in response.data
