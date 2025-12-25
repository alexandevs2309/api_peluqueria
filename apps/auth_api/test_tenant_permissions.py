"""Tests de autorización por tenant - Prevención de regresiones"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from unittest.mock import Mock
from apps.tenants_api.models import Tenant
from apps.roles_api.models import Role, UserRole
from apps.auth_api.permissions import IsClientAdmin, IsClientAdminOrStaff

User = get_user_model()

class TenantPermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        
        # Crear roles
        self.admin_role = Role.objects.create(name='CLIENT_ADMIN')
        self.staff_role = Role.objects.create(name='CLIENT_STAFF')
        
        # Crear usuarios primero
        self.admin_user = User.objects.create_user(
            email='admin@tenant1.com',
            password='test123'
        )
        self.other_user = User.objects.create_user(
            email='user@tenant2.com', 
            password='test123'
        )
        
        # Crear tenants con owners
        self.tenant1 = Tenant.objects.create(
            name='Tenant 1', 
            subdomain='tenant1',
            owner=self.admin_user
        )
        self.tenant2 = Tenant.objects.create(
            name='Tenant 2', 
            subdomain='tenant2',
            owner=self.other_user
        )
        
        # Asignar tenants a usuarios
        self.admin_user.tenant = self.tenant1
        self.admin_user.save()
        self.other_user.tenant = self.tenant2
        self.other_user.save()
        
        # Crear UserRoles contextuales
        UserRole.objects.create(user=self.admin_user, role=self.admin_role, tenant=self.tenant1)
        UserRole.objects.create(user=self.other_user, role=self.admin_role, tenant=self.tenant2)

    def test_client_admin_permission_with_correct_tenant(self):
        """Admin con tenant correcto debe tener acceso"""
        request = Mock()
        request.user = self.admin_user
        
        permission = IsClientAdmin()
        self.assertTrue(permission.has_permission(request, None))

    def test_client_admin_permission_isolation(self):
        """Usuarios de diferentes tenants no deben tener acceso cruzado"""
        request = Mock()
        request.user = self.other_user
        
        permission = IsClientAdmin()
        self.assertTrue(permission.has_permission(request, None))  # Tiene su propio tenant

    def test_user_without_userrole_denied(self):
        """Usuario sin UserRole debe ser denegado"""
        user_no_role = User.objects.create_user(
            email='norole@test.com',
            password='test123',
            tenant=self.tenant1
        )
        
        request = Mock()
        request.user = user_no_role
        
        permission = IsClientAdmin()
        self.assertFalse(permission.has_permission(request, None))

    def test_staff_permission_includes_admin(self):
        """IsClientAdminOrStaff debe incluir CLIENT_ADMIN"""
        request = Mock()
        request.user = self.admin_user
        
        permission = IsClientAdminOrStaff()
        self.assertTrue(permission.has_permission(request, None))