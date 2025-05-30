import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from django.contrib.auth.models import Permission
from apps.auth_api.factories import UserFactory
from apps.auth_api.models import User
from apps.roles_api.models import Role, UserRole, AdminActionLog
from apps.roles_api.utils import log_admin_action

@pytest.fixture
def admin_user():
    user = UserFactory(is_email_verified=True)
    role = Role.objects.create(name='Admin')  # Rol en roles_api.models.Role
    UserRole.objects.create(user=user, role=role)
    return user

@pytest.fixture
def client_user():
    user = UserFactory(is_email_verified=True)
    role = Role.objects.create(name='Client')
    UserRole.objects.create(user=user, role=role)
    return user

@pytest.mark.django_db
def test_list_roles_as_admin(admin_user):
    # Crear roles
    Role.objects.create(name='Stylist')
    Role.objects.create(name='Utility')

    # Autenticar como admin
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # Listar roles
    response = client.get(reverse('role-list'))
    assert response.status_code == 200
    assert response.data['count'] == 3  # admin, Stylist, Utility
    assert len(response.data['results']) == 3
    assert any(r['name'] == 'admin' for r in response.data['results'])

    # Verificar AdminActionLog
    log = AdminActionLog.objects.filter(user=admin_user, action='List roles').first()
    assert log is not None

@pytest.mark.django_db
def test_list_roles_as_non_admin(client_user):
    # Crear roles
    Role.objects.create(name='admin')

    # Autenticar como Client
    client = APIClient()
    client.force_authenticate(user=client_user)

    # Intentar listar roles
    response = client.get(reverse('role-list'))
    assert response.status_code == 403
    assert 'detail' in response.data
    assert not AdminActionLog.objects.filter(user=client_user, action='List roles').exists()

@pytest.mark.django_db
def test_retrieve_role_as_admin(admin_user):
    # Crear rol
    role = Role.objects.create(name='Stylist')
    permission = Permission.objects.first()
    role.permissions.add(permission)

    # Autenticar como admin
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # Obtener rol
    response = client.get(reverse('role-detail', kwargs={'pk': role.id}))
    assert response.status_code == 200
    assert response.data['name'] == 'Stylist'
    assert len(response.data['permissions']) == 1

    # Verificar AdminActionLog
    log = AdminActionLog.objects.filter(user=admin_user, action='Retrieve role').first()
    assert log is not None

@pytest.mark.django_db
def test_create_role_as_admin(admin_user):
    # Autenticar como admin
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # Crear un nuevo rol
    data = {
        'name': 'Manager',
        'description': 'Role for managers',
        'permissions': [Permission.objects.first().id]
    }
    response = client.post(reverse('role-list'), data, format='json')
    assert response.status_code == 201
    assert Role.objects.filter(name='Manager').exists()
    role = Role.objects.get(name='Manager')
    assert role.description == 'Role for managers'
    assert role.permissions.count() == 1

    # Verificar AdminActionLog
    log = AdminActionLog.objects.filter(user=admin_user, action='Create role').first()
    assert log is not None

@pytest.mark.django_db
def test_update_role_as_admin(admin_user):
    # Crear rol
    role = Role.objects.create(name='Stylist')

    # Autenticar como admin
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # Actualizar rol
    data = {
        'name': 'SeniorStylist',
        'description': 'Rol actualizado'
    }
    response = client.put(reverse('role-detail', kwargs={'pk': role.id}), data, format='json')
    assert response.status_code == 200
    role.refresh_from_db()
    assert role.name == 'SeniorStylist'
    assert role.description == 'Rol actualizado'

    # Verificar AdminActionLog
    log = AdminActionLog.objects.filter(user=admin_user, action='Update role').first()
    assert log is not None

@pytest.mark.django_db
def test_delete_role_as_admin(admin_user):
    # Crear rol
    role = Role.objects.create(name='Utility')

    # Autenticar como admin
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # Eliminar rol
    response = client.delete(reverse('role-detail', kwargs={'pk': role.id}))
    assert response.status_code == 204
    assert not Role.objects.filter(name='Utility').exists()

    # Verificar AdminActionLog
    log = AdminActionLog.objects.filter(user=admin_user, action='Delete role').first()
    assert log is not None

@pytest.mark.django_db
def test_list_permissions_as_admin(admin_user):
    # Autenticar como admin
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # Listar permisos
    response = client.get(reverse('list_permissions'))
    assert response.status_code == 200
    assert len(response.data['results']) > 0  # Al menos un permiso
    assert 'codename' in response.data['results'][0]

    # Verificar AdminActionLog
    log = AdminActionLog.objects.filter(user=admin_user, action='List permissions').first()
    assert log is not None

@pytest.mark.django_db
def test_roles_unauthenticated():
    # Crear rol
    Role.objects.create(name='admin')

    # Cliente no autenticado
    client = APIClient()

    # Intentar listar roles
    response = client.get(reverse('role-list'))
    assert response.status_code == 401
    assert 'detail' in response.data