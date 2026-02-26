"""
Tests de seguridad IDOR (Insecure Direct Object Reference)
Valida que usuarios de un tenant NO puedan acceder a recursos de otro tenant.
"""
import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.auth_api.models import User
from apps.tenants_api.models import Tenant
from apps.employees_api.models import Employee
from apps.clients_api.models import Client
from apps.appointments_api.models import Appointment
from apps.pos_api.models import Sale
from django.utils import timezone


@pytest.mark.django_db
class IDORSecurityTests(TestCase):
    """Tests de seguridad cross-tenant"""
    
    def setUp(self):
        """Setup: Crear 2 tenants con usuarios y datos"""
        
        # Tenant A
        self.tenant_a = Tenant.objects.create(
            name="Barbería A",
            subdomain="tenant-a",
            subscription_plan="premium",
            subscription_status="active"
        )
        
        self.user_a = User.objects.create_user(
            email="admin@tenant-a.com",
            password="test123",
            full_name="Admin A",
            tenant=self.tenant_a,
            role="Client-Admin"
        )
        
        self.employee_a = Employee.objects.create(
            user=self.user_a,
            tenant=self.tenant_a,
            is_active=True
        )
        
        self.client_a = Client.objects.create(
            full_name="Cliente A",
            email="cliente@tenant-a.com",
            tenant=self.tenant_a
        )
        
        # Tenant B
        self.tenant_b = Tenant.objects.create(
            name="Barbería B",
            subdomain="tenant-b",
            subscription_plan="basic",
            subscription_status="active"
        )
        
        self.user_b = User.objects.create_user(
            email="admin@tenant-b.com",
            password="test123",
            full_name="Admin B",
            tenant=self.tenant_b,
            role="Client-Admin"
        )
        
        self.employee_b = Employee.objects.create(
            user=self.user_b,
            tenant=self.tenant_b,
            is_active=True
        )
        
        self.client_b = Client.objects.create(
            full_name="Cliente B",
            email="cliente@tenant-b.com",
            tenant=self.tenant_b
        )
        
        # API Clients
        self.api_client_a = APIClient()
        self.api_client_b = APIClient()
    
    def test_idor_employee_retrieve_cross_tenant(self):
        """Usuario de Tenant A NO puede ver Employee de Tenant B"""
        self.api_client_a.force_authenticate(user=self.user_a)
        
        # Simular request.tenant
        self.api_client_a.credentials(HTTP_X_TENANT_SUBDOMAIN='tenant-a')
        
        response = self.api_client_a.get(f'/api/employees/{self.employee_b.id}/')
        
        # Debe retornar 404 (no 403 para no revelar existencia)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_idor_employee_update_cross_tenant(self):
        """Usuario de Tenant A NO puede actualizar Employee de Tenant B"""
        self.api_client_a.force_authenticate(user=self.user_a)
        
        response = self.api_client_a.patch(
            f'/api/employees/{self.employee_b.id}/',
            {'is_active': False}
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Verificar que NO se modificó
        self.employee_b.refresh_from_db()
        self.assertTrue(self.employee_b.is_active)
    
    def test_idor_employee_delete_cross_tenant(self):
        """Usuario de Tenant A NO puede eliminar Employee de Tenant B"""
        self.api_client_a.force_authenticate(user=self.user_a)
        
        response = self.api_client_a.delete(f'/api/employees/{self.employee_b.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Verificar que NO se eliminó
        self.assertTrue(Employee.objects.filter(id=self.employee_b.id).exists())
    
    def test_idor_client_retrieve_cross_tenant(self):
        """Usuario de Tenant A NO puede ver Client de Tenant B"""
        self.api_client_a.force_authenticate(user=self.user_a)
        
        response = self.api_client_a.get(f'/api/clients/{self.client_b.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_idor_client_list_isolation(self):
        """Usuario de Tenant A solo ve sus propios clientes"""
        self.api_client_a.force_authenticate(user=self.user_a)
        
        response = self.api_client_a.get('/api/clients/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Solo debe ver client_a
        client_ids = [c['id'] for c in response.data.get('results', response.data)]
        self.assertIn(self.client_a.id, client_ids)
        self.assertNotIn(self.client_b.id, client_ids)
    
    def test_idor_appointment_cross_tenant(self):
        """Usuario de Tenant A NO puede ver Appointment de Tenant B"""
        appointment_b = Appointment.objects.create(
            tenant=self.tenant_b,
            client=self.client_b,
            stylist=self.user_b,
            date_time=timezone.now() + timezone.timedelta(days=1),
            status='scheduled'
        )
        
        self.api_client_a.force_authenticate(user=self.user_a)
        
        response = self.api_client_a.get(f'/api/appointments/{appointment_b.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_idor_sale_cross_tenant(self):
        """Usuario de Tenant A NO puede ver Sale de Tenant B"""
        sale_b = Sale.objects.create(
            tenant=self.tenant_b,
            user=self.user_b,
            employee=self.employee_b,
            client=self.client_b,
            total=100.00,
            paid=100.00,
            payment_method='cash'
        )
        
        self.api_client_a.force_authenticate(user=self.user_a)
        
        response = self.api_client_a.get(f'/api/sales/{sale_b.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_idor_custom_action_cross_tenant(self):
        """Usuario de Tenant A NO puede ejecutar acciones custom en recursos de Tenant B"""
        self.api_client_a.force_authenticate(user=self.user_a)
        
        # Intentar obtener stats de employee de otro tenant
        response = self.api_client_a.get(f'/api/employees/{self.employee_b.id}/stats/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_superadmin_can_access_all_tenants(self):
        """SuperAdmin puede ver recursos de todos los tenants"""
        superadmin = User.objects.create_superuser(
            email="superadmin@system.com",
            password="super123",
            full_name="Super Admin"
        )
        
        api_client = APIClient()
        api_client.force_authenticate(user=superadmin)
        
        # Puede ver employee de Tenant A
        response_a = api_client.get(f'/api/employees/{self.employee_a.id}/')
        self.assertEqual(response_a.status_code, status.HTTP_200_OK)
        
        # Puede ver employee de Tenant B
        response_b = api_client.get(f'/api/employees/{self.employee_b.id}/')
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)
    
    def test_user_can_access_own_tenant_resources(self):
        """Usuario puede acceder a recursos de su propio tenant"""
        self.api_client_a.force_authenticate(user=self.user_a)
        
        response = self.api_client_a.get(f'/api/employees/{self.employee_a.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.employee_a.id)


@pytest.mark.django_db
class AdminPanelSecurityTests(TestCase):
    """Tests de seguridad del Django Admin"""
    
    def setUp(self):
        """Setup: Crear tenants y usuarios"""
        self.tenant_a = Tenant.objects.create(
            name="Tenant A",
            subdomain="tenant-a"
        )
        
        self.tenant_b = Tenant.objects.create(
            name="Tenant B",
            subdomain="tenant-b"
        )
        
        self.admin_a = User.objects.create_user(
            email="admin@tenant-a.com",
            password="test123",
            tenant=self.tenant_a,
            is_staff=True,
            role="Client-Admin"
        )
        
        self.employee_a = Employee.objects.create(
            user=self.admin_a,
            tenant=self.tenant_a
        )
        
        self.employee_b = Employee.objects.create(
            user=User.objects.create_user(
                email="user@tenant-b.com",
                password="test123",
                tenant=self.tenant_b
            ),
            tenant=self.tenant_b
        )
        
        self.client = APIClient()
    
    def test_admin_only_sees_own_tenant_employees(self):
        """Admin de Tenant A solo ve employees de su tenant en admin panel"""
        self.client.force_login(self.admin_a)
        
        from apps.employees_api.admin import EmployeeAdmin
        from apps.employees_api.models import Employee
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/admin/employees_api/employee/')
        request.user = self.admin_a
        
        admin = EmployeeAdmin(Employee, AdminSite())
        queryset = admin.get_queryset(request)
        
        # Solo debe ver employee_a
        self.assertIn(self.employee_a, queryset)
        self.assertNotIn(self.employee_b, queryset)
