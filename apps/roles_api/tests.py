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
    # Asegúrate de que el rol 'Admin' se crea o existe ANTES de intentar asignarlo
    # La mayúscula es importante: 'Admin' vs 'admin'
    admin_role, created = Role.objects.get_or_create(name='Admin')
    UserRole.objects.create(user=user, role=admin_role)
    # Debugging: verificar si el usuario tiene el rol
    print(f"\nDEBUG: Admin user created: {user.email}")
    assigned_roles = user.roles.values_list('name', flat=True)  # CORREGIDO: usar roles en lugar de assigned_users
    print(f"DEBUG: Admin user has roles: {list(assigned_roles)}")
    assert 'Admin' in assigned_roles # Asegúrate de que el rol está asignado
    return user

@pytest.fixture
def client_user():
    user = UserFactory(is_email_verified=True)
    client_role, created = Role.objects.get_or_create(name='Client')
    UserRole.objects.create(user=user, role=client_role)
    print(f"\nDEBUG: Client user created: {user.email}")
    assigned_roles = user.roles.values_list('name', flat=True)  # CORREGIDO: usar roles en lugar de assigned_users
    print(f"DEBUG: Client user has roles: {list(assigned_roles)}")
    assert 'Client' in assigned_roles
    return user

@pytest.mark.django_db
def test_list_roles_as_admin(admin_user):
    # Crear roles adicionales
    Role.objects.get_or_create(name='Stylist')
    Role.objects.get_or_create(name='Utility')

    # Autenticar como admin
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # Listar roles
    response = client.get(reverse('role-list'))
    assert response.status_code == 200
    
    # Verificar que tenemos al menos 3 roles (admin, stylist, utility)
    assert response.data['count'] >= 3
    assert len(response.data['results']) >= 3
    
    # Verificar que existe el rol admin
    role_names = [r['name'] for r in response.data['results']]
    assert 'Admin' in role_names

    # Verificar AdminActionLog
    log = AdminActionLog.objects.filter(user=admin_user, action='List roles').first()
    assert log is not None

@pytest.mark.django_db
def test_list_roles_as_non_admin(client_user):
    # Autenticar como Client
    client = APIClient()
    client.force_authenticate(user=client_user)

    # Intentar listar roles (debería fallar)
    response = client.get(reverse('role-list'))
    assert response.status_code == 403
    assert 'detail' in response.data
    
    # Verificar que NO se creó log para usuario no admin
    assert not AdminActionLog.objects.filter(user=client_user, action='List roles').exists()

@pytest.mark.django_db
def test_retrieve_role_as_admin(admin_user):
    # Crear rol
    role = Role.objects.create(name='Stylist')
    
    # Agregar un permiso si existe
    permission = Permission.objects.first()
    if permission:
        role.permissions.add(permission)

    # Autenticar como admin
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # Obtener rol
    response = client.get(reverse('role-detail', kwargs={'pk': role.id}))
    assert response.status_code == 200
    assert response.data['name'] == 'Stylist'
    
    # Verificar permisos si existen
    if permission:
        assert len(response.data['permissions']) >= 1

    # Verificar AdminActionLog
    log = AdminActionLog.objects.filter(user=admin_user, action='Retrieve role').first()
    assert log is not None

@pytest.mark.django_db
def test_create_role_as_admin(admin_user):
    # Autenticar como admin
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # Obtener un permiso existente
    permission = Permission.objects.first()
    
    # Crear un nuevo rol
    data = {
        'name': 'manager',
        'description': 'Role for managers'
    }
    
    # Agregar permisos solo si existen
    if permission:
        data['permissions'] = [permission.id]
    
    response = client.post(reverse('role-list'), data, format='json')
    assert response.status_code == 201
    
    # Verificar que el rol fue creado
    assert Role.objects.filter(name='manager').exists()
    role = Role.objects.get(name='manager')
    assert role.description == 'Role for managers'
    
    # Verificar permisos si se agregaron
    if permission:
        assert role.permissions.count() >= 1

    # Verificar AdminActionLog
    log = AdminActionLog.objects.filter(user=admin_user, action='Create role').first()
    assert log is not None

@pytest.mark.django_db
def test_update_role_as_admin(admin_user):
    # Crear rol
    role = Role.objects.create(name='Stylist', description='Original description')

    # Autenticar como admin
    client = APIClient()
    client.force_authenticate(user=admin_user)

    # Actualizar rol
    data = {
        'name': 'senior_stylist',
        'description': 'Updated description'
    }
    
    response = client.put(reverse('role-detail', kwargs={'pk': role.id}), data, format='json')
    assert response.status_code == 200
    
    # Verificar actualización
    role.refresh_from_db()
    assert role.name == 'senior_stylist'
    assert role.description == 'Updated description'

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
    
    # Verificar que el rol fue eliminado
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
    
    # Verificar que hay permisos en la respuesta
    assert len(response.data['results']) > 0
    assert 'codename' in response.data['results'][0]

    # Verificar AdminActionLog
    log = AdminActionLog.objects.filter(user=admin_user, action='List permissions').first()
    assert log is not None

@pytest.mark.django_db
def test_roles_unauthenticated():
    # Cliente no autenticado
    client = APIClient()

    # Intentar listar roles
    response = client.get(reverse('role-list'))
    assert response.status_code == 401
    assert 'detail' in response.data

@pytest.mark.django_db
def test_retrieve_role_as_non_admin(client_user):
    # Crear rol
    role = Role.objects.create(name='test_role')
    
    # Autenticar como client (no admin)
    client = APIClient()
    client.force_authenticate(user=client_user)

    # Intentar obtener rol (debería fallar)
    response = client.get(reverse('role-detail', kwargs={'pk': role.id}))
    assert response.status_code == 403

@pytest.mark.django_db
def test_create_role_as_non_admin(client_user):
    # Autenticar como client (no admin)
    client = APIClient()
    client.force_authenticate(user=client_user)

    # Intentar crear rol (debería fallar)
    data = {'name': 'new_role', 'description': 'Test role'}
    response = client.post(reverse('role-list'), data, format='json')
    assert response.status_code == 403