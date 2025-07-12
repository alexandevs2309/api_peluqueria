from django.http import HttpRequest
import pytest
from rest_framework.test import APIClient, APIRequestFactory
from django.urls import reverse
from django.contrib.auth.models import Permission

from apps.roles_api.permissions import IsActiveAndRolePermission
from apps.auth_api.factories import UserFactory
from apps.auth_api.models import User
from apps.roles_api.models import Role, UserRole, AdminActionLog
from apps.roles_api.permissions import RolePermission, role_permission_for
from apps.auth_api.utils import get_client_ip


@pytest.fixture
def admin_user(db):
    user = UserFactory(is_email_verified=True)
    admin_role, _ = Role.objects.get_or_create(name='Admin')
    UserRole.objects.get_or_create(user=user, role=admin_role)
    return user

@pytest.fixture
def client_user(db):
    user = UserFactory(is_email_verified=True)
    client_role, _ = Role.objects.get_or_create(name='Client')
    UserRole.objects.get_or_create(user=user, role=client_role)
    return user

@pytest.mark.django_db
def test_list_roles_as_admin(admin_user):
    Role.objects.get_or_create(name='Stylist')
    Role.objects.get_or_create(name='Utility')

    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.get(reverse('role-list'))
    assert response.status_code == 200
    assert response.data['count'] >= 3
    role_names = [r['name'] for r in response.data['results']]
    assert 'Admin' in role_names

    assert AdminActionLog.objects.filter(user=admin_user, action='List roles').exists()

@pytest.mark.django_db
def test_list_roles_as_non_admin(client_user):
    client = APIClient()
    client.force_authenticate(user=client_user)

    response = client.get(reverse('role-list'))
    assert response.status_code == 403
    assert 'detail' in response.data

    assert not AdminActionLog.objects.filter(user=client_user, action='List roles').exists()

@pytest.mark.django_db
def test_retrieve_role_as_admin(admin_user):
    role, _ = Role.objects.get_or_create(name='Stylist')
    permission = Permission.objects.first()
    if permission:
        role.permissions.add(permission)

    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.get(reverse('role-detail', kwargs={'pk': role.id}))
    assert response.status_code == 200
    assert response.data['name'] == 'Stylist'
    if permission:
        assert len(response.data['permissions']) >= 1

    assert AdminActionLog.objects.filter(user=admin_user, action='Retrieve role').exists()

@pytest.mark.django_db
def test_create_role_as_admin(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    permission = Permission.objects.first()
    data = {
        'name': 'Manager',
        'description': 'Role for managers',
    }
    if permission:
        data['permissions'] = [permission.id]

    response = client.post(reverse('role-list'), data, format='json')
    assert response.status_code == 201
    role = Role.objects.get(name='Manager')
    assert role.description == 'Role for managers'
    if permission:
        assert role.permissions.exists()

    assert AdminActionLog.objects.filter(user=admin_user, action='Create role').exists()

@pytest.mark.django_db
def test_update_role_as_admin(admin_user):
    role, _ = Role.objects.get_or_create(name='Stylist', defaults={'description': 'Original description'})

    client = APIClient()
    client.force_authenticate(user=admin_user)

    data = {'name': 'Senior Stylist', 'description': 'Updated description'}
    response = client.put(reverse('role-detail', kwargs={'pk': role.id}), data, format='json')
    assert response.status_code == 200

    role.refresh_from_db()
    assert role.name == 'Senior Stylist'
    assert role.description == 'Updated description'

    assert AdminActionLog.objects.filter(user=admin_user, action='Update role').exists()

@pytest.mark.django_db
def test_delete_role_as_admin(admin_user):
    role, _ = Role.objects.get_or_create(name='Utility')

    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.delete(reverse('role-detail', kwargs={'pk': role.id}))
    assert response.status_code == 204
    assert not Role.objects.filter(name='Utility').exists()

    assert AdminActionLog.objects.filter(user=admin_user, action='Delete role').exists()

@pytest.mark.django_db
def test_list_permissions_as_admin(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.get(reverse('list_permissions'))
    assert response.status_code == 200
    assert response.data['results']
    assert 'codename' in response.data['results'][0]

    assert AdminActionLog.objects.filter(user=admin_user, action='List permissions').exists()

@pytest.mark.django_db
def test_roles_unauthenticated():
    client = APIClient()
    response = client.get(reverse('role-list'))
    assert response.status_code == 401
    assert 'detail' in response.data

@pytest.mark.django_db
def test_retrieve_role_as_non_admin(client_user):
    role, _ = Role.objects.get_or_create(name='Test Role')

    client = APIClient()
    client.force_authenticate(user=client_user)

    response = client.get(reverse('role-detail', kwargs={'pk': role.id}))
    assert response.status_code == 403

@pytest.mark.django_db
def test_create_role_as_non_admin(client_user):
    client = APIClient()
    client.force_authenticate(user=client_user)

    data = {'name': 'New Role', 'description': 'Test role'}
    response = client.post(reverse('role-list'), data, format='json')
    assert response.status_code == 403

@pytest.mark.django_db
def test_roles_api_permission_denies_anonymous():
    factory = APIRequestFactory()
    request = factory.get('/')
    request.user = None
    perm = RolePermission(allowed_roles=['Admin'])
    assert not perm.has_permission(request, None)

@pytest.mark.django_db
def test_roles_api_permission_allows_superuser():
    user = User.objects.create_superuser(email="super@test.com", password="123456", full_name="Super User")
    factory = APIRequestFactory()
    request = factory.get('/')
    request.user = user
    perm = RolePermission(allowed_roles=['Any'])
    assert perm.has_permission(request, None)

@pytest.mark.django_db
def test_roles_api_permission_allows_with_role():
    user = User.objects.create_user(email="user@test.com", password="123456", full_name="User Test")
    role, _ = Role.objects.get_or_create(name="Stylist")
    UserRole.objects.get_or_create(user=user, role=role)

    factory = APIRequestFactory()
    request = factory.get('/')
    request.user = user
    perm = RolePermission(allowed_roles=['Stylist'])
    assert perm.has_permission(request, None)

@pytest.mark.django_db
def test_roles_api_permission_denies_without_role():
    user = User.objects.create_user(email="user2@test.com", password="123456", full_name="User2 Test")
    factory = APIRequestFactory()
    request = factory.get('/')
    request.user = user
    perm = RolePermission(allowed_roles=['Manager'])
    assert not perm.has_permission(request, None)


@pytest.mark.django_db
def test_inactive_user_denied_permission():
    user = UserFactory(is_email_verified=True, is_active=False)
    role, _ = Role.objects.get_or_create(name="Admin")
    UserRole.objects.create(user=user, role=role)

    factory = APIRequestFactory()
    request = factory.get('/')
    request.user = user

    perm = IsActiveAndRolePermission(['Admin'])
    assert not perm.has_permission(request, None)


@pytest.mark.django_db
def test_role_permission_for_dynamic_class():
    user = User.objects.create_user(email="dynamic@test.com", password="123456", full_name="Dynamic Test")
    role, _ = Role.objects.get_or_create(name="Manager")
    UserRole.objects.get_or_create(user=user, role=role)

    factory = APIRequestFactory()
    request = factory.get('/')
    request.user = user

    DynamicPerm = role_permission_for(['Manager'])
    perm_instance = DynamicPerm()
    assert perm_instance.has_permission(request, None)


def test_get_client_ip_with_forwarded_for():
    request = HttpRequest()
    request.META['HTTP_X_FORWARDED_FOR'] = '1.2.3.4, 5.6.7.8'
    ip = get_client_ip(request)
    assert ip == '1.2.3.4'

def test_get_client_ip_without_forwarded_for():
    request = HttpRequest()
    request.META['REMOTE_ADDR'] = '9.8.7.6'
    ip = get_client_ip(request)
    assert ip == '9.8.7.6'

@pytest.mark.django_db
def test_role_permission_denied_for_inactive_user():
    user = User.objects.create_user(email="inactive@test.com", password="123456", full_name="Inactive User", is_active=False)
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = user
    perm = RolePermission(allowed_roles=["Admin"])
    assert not perm.has_permission(request, None)


def test_get_client_ip_with_forwarded_for():
    request = HttpRequest()
    request.META['HTTP_X_FORWARDED_FOR'] = '1.2.3.4'
    ip = get_client_ip(request)
    assert ip == '1.2.3.4'

def test_get_client_ip_without_forwarded_for():
    request = HttpRequest()
    request.META['REMOTE_ADDR'] = '5.6.7.8'
    ip = get_client_ip(request)
    assert ip == '5.6.7.8'