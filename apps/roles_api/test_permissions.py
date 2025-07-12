import pytest
from rest_framework.test import APIRequestFactory
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from apps.roles_api.models import Role, UserRole
from apps.roles_api.permissions import RolePermission, IsActiveAndRolePermission, role_permission_for
from apps.roles_api.decorators import role_required, admin_action_log, permission_required
from apps.roles_api.models import AdminActionLog

User = get_user_model()

@pytest.fixture
def factory():
    return APIRequestFactory()

@pytest.fixture
def role_admin():
    return Role.objects.get_or_create(name="Admin")[0]

@pytest.fixture
def role_client():
    return Role.objects.get_or_create(name="Client")[0]

@pytest.fixture
def admin_user(role_admin):
    user = User.objects.create_user(email="admin@test.com", password="123456", full_name="Admin User")
    UserRole.objects.create(user=user, role=role_admin)
    return user

@pytest.fixture
def client_user(role_client):
    user = User.objects.create_user(email="client@test.com", password="123456", full_name="Client User")
    UserRole.objects.create(user=user, role=role_client)
    return user

@pytest.mark.django_db
def test_role_permission_allows_correct_role(factory, admin_user):
    request = factory.get("/")
    request.user = admin_user
    perm = RolePermission(allowed_roles=["Admin"])
    assert perm.has_permission(request, None)

@pytest.mark.django_db
def test_role_permission_denies_incorrect_role(factory, client_user):
    request = factory.get("/")
    request.user = client_user
    perm = RolePermission(allowed_roles=["Admin"])
    assert not perm.has_permission(request, None)

@pytest.mark.django_db
def test_is_active_and_role_permission_allows(factory, admin_user):
    request = factory.get("/")
    request.user = admin_user
    perm = IsActiveAndRolePermission(allowed_roles=["Admin"])
    assert perm.has_permission(request, None)

@pytest.mark.django_db
def test_is_active_and_role_permission_denies_if_inactive(factory, admin_user):
    admin_user.is_active = False
    admin_user.save()
    request = factory.get("/")
    request.user = admin_user
    perm = IsActiveAndRolePermission(allowed_roles=["Admin"])
    assert not perm.has_permission(request, None)

@pytest.mark.django_db
def test_role_permission_for_dynamic(factory, admin_user):
    request = factory.get("/")
    request.user = admin_user
    DynamicPerm = role_permission_for(["Admin"])
    perm = DynamicPerm()
    assert perm.has_permission(request, None)

@pytest.mark.django_db
def test_role_required_decorator_allows(admin_user):
    @role_required("Admin")
    def view(request):
        return Response({"ok": True})
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = admin_user
    response = view(request)
    assert response.status_code == 200
    assert response.data["ok"]

@pytest.mark.django_db
def test_role_required_decorator_denies(client_user):
    @role_required("Admin")
    def view(request):
        return Response({"ok": True})
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = client_user
    response = view(request)
    assert response.status_code == 403

@pytest.mark.django_db
def test_admin_action_log_decorator_creates_log(admin_user):
    @admin_action_log("Test Action")
    def view(request):
        return Response({"ok": True})
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = admin_user
    response = view(request)
    assert response.status_code == 200
    assert AdminActionLog.objects.filter(user=admin_user, action="Test Action").exists()

@pytest.mark.django_db
def test_permission_required_decorator_allows(factory, admin_user):
    @permission_required(RolePermission, allowed_roles=["Admin"])
    def view(request):
        return Response({"ok": True})
    request = factory.get("/")
    request.user = admin_user
    response = view(request)
    assert response.status_code == 200
    assert response.data["ok"]

@pytest.mark.django_db
def test_permission_required_decorator_denies(factory, client_user):
    @permission_required(RolePermission, allowed_roles=["Admin"])
    def view(request):
        return Response({"ok": True})
    request = factory.get("/")
    request.user = client_user
    response = view(request)
    assert response.status_code == 403
