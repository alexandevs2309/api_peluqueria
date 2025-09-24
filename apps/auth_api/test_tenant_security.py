import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from apps.tenants_api.models import Tenant
from apps.tenants_api.middleware import TenantMiddleware
from apps.roles_api.models import Role
from django.http import JsonResponse

User = get_user_model()

class TenantSecurityTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = TenantMiddleware()
        
        # Crear roles
        self.super_admin_role = Role.objects.create(name='Super-Admin', level='global')
        self.client_admin_role = Role.objects.create(name='Client-Admin', level='tenant')
        
        # Crear tenants
        self.tenant1 = Tenant.objects.create(
            name='Peluquería A',
            subdomain='peluqueria-a',
            owner_id=1
        )
        self.tenant2 = Tenant.objects.create(
            name='Peluquería B', 
            subdomain='peluqueria-b',
            owner_id=2
        )
        
        # Crear usuarios
        self.super_admin = User.objects.create_user(
            email='super@admin.com',
            password='test123',
            full_name='Super Admin'
        )
        self.super_admin.roles.add(self.super_admin_role)
        
        self.client_admin1 = User.objects.create_user(
            email='admin1@test.com',
            password='test123',
            full_name='Admin 1',
            tenant=self.tenant1
        )
        self.client_admin1.roles.add(self.client_admin_role)
        
        self.client_admin2 = User.objects.create_user(
            email='admin2@test.com',
            password='test123',
            full_name='Admin 2',
            tenant=self.tenant2
        )
        self.client_admin2.roles.add(self.client_admin_role)

    def test_super_admin_no_tenant_restriction(self):
        """Super-Admin puede acceder sin restricción de tenant"""
        request = self.factory.get('/api/clients/')
        request.user = self.super_admin
        
        response = self.middleware.process_request(request)
        
        self.assertIsNone(response)  # No hay restricción
        self.assertIsNone(request.tenant)  # Sin tenant asignado

    def test_client_admin_tenant_restriction(self):
        """Client-Admin solo puede acceder a su tenant"""
        request = self.factory.get('/api/clients/')
        request.user = self.client_admin1
        
        response = self.middleware.process_request(request)
        
        self.assertIsNone(response)  # Acceso permitido
        self.assertEqual(request.tenant, self.tenant1)  # Tenant correcto

    def test_user_without_tenant_denied(self):
        """Usuario sin tenant debe ser denegado"""
        user_no_tenant = User.objects.create_user(
            email='notenant@test.com',
            password='test123',
            full_name='No Tenant'
        )
        user_no_tenant.roles.add(self.client_admin_role)
        
        request = self.factory.get('/api/clients/')
        request.user = user_no_tenant
        
        response = self.middleware.process_request(request)
        
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 403)

    def test_exempt_paths_allowed(self):
        """Rutas exentas deben permitir acceso"""
        exempt_paths = ['/api/auth/login/', '/api/schema/', '/api/healthz/']
        
        for path in exempt_paths:
            request = self.factory.get(path)
            request.user = self.client_admin1
            
            response = self.middleware.process_request(request)
            
            self.assertIsNone(response, f"Path {path} should be exempt")

    def test_tenant_isolation(self):
        """Verificar que los datos están aislados por tenant"""
        # Este test requeriría modelos con tenant_id
        # Por ahora verificamos que el middleware asigna el tenant correcto
        
        request1 = self.factory.get('/api/clients/')
        request1.user = self.client_admin1
        self.middleware.process_request(request1)
        
        request2 = self.factory.get('/api/clients/')
        request2.user = self.client_admin2
        self.middleware.process_request(request2)
        
        self.assertEqual(request1.tenant.id, self.tenant1.id)
        self.assertEqual(request2.tenant.id, self.tenant2.id)
        self.assertNotEqual(request1.tenant.id, request2.tenant.id)