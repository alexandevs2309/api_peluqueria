# apps/auth_api/tests_security.py
"""
Tests de seguridad para sistema multi-tenant
"""
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan
from apps.settings_api.models import SystemSettings

User = get_user_model()


class MultiTenantSecurityTests(TestCase):
    """Tests de seguridad multi-tenant"""
    
    def setUp(self):
        self.owner = User.objects.create_superuser(
            email='owner@example.com',
            password='pass123',
            full_name='Test Owner',
            role='SuperAdmin'
        )
        settings = SystemSettings.get_settings()
        settings.require_email_verification = False
        settings.enable_mfa = False
        settings.save(update_fields=['require_email_verification', 'enable_mfa'])

        # Crear plan
        self.plan = SubscriptionPlan.objects.create(
            name='test',
            price=0,
            max_users=10
        )
        
        # Crear tenants
        self.tenant_a = Tenant.objects.create(
            name='Tenant A',
            subdomain='tenant-a',
            subscription_plan=self.plan,
            owner=self.owner
        )
        self.tenant_b = Tenant.objects.create(
            name='Tenant B',
            subdomain='tenant-b',
            subscription_plan=self.plan,
            owner=self.owner
        )
        
        # Crear usuarios
        self.admin_a = User.objects.create_user(
            email='admin@tenant-a.com',
            password='pass123',
            full_name='Admin Tenant A',
            tenant=self.tenant_a,
            role='Client-Admin'
        )
        self.staff_a = User.objects.create_user(
            email='staff@tenant-a.com',
            password='pass123',
            full_name='Staff Tenant A',
            tenant=self.tenant_a,
            role='Client-Staff'
        )
        self.admin_b = User.objects.create_user(
            email='admin@tenant-b.com',
            password='pass123',
            full_name='Admin Tenant B',
            tenant=self.tenant_b,
            role='Client-Admin'
        )
        
        self.client = APIClient()
    
    def test_login_requires_explicit_tenant_for_client_users(self):
        """Login de cliente debe fallar sin tenant explícito."""
        response = self.client.post('/api/auth/login/', {
            'email': 'admin@tenant-a.com',
            'password': 'pass123'
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('tenant', str(response.data))

    @override_settings(ALLOWED_HOSTS=['testserver', 'api-peluqueria-p25h.onrender.com'])
    def test_login_does_not_infer_tenant_from_technical_host(self):
        """Hosts técnicos de Render/Netlify no deben convertirse en tenants."""
        response = self.client.post(
            '/api/auth/login/',
            {
                'email': 'admin@tenant-a.com',
                'password': 'pass123'
            },
            HTTP_HOST='api-peluqueria-p25h.onrender.com'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('tenant', str(response.data))
        self.assertNotIn('Credenciales inválidas', str(response.data))

    def test_login_accepts_tenant_field(self):
        """Login debe aceptar tenant como campo explícito principal."""
        response = self.client.post('/api/auth/login/', {
            'email': 'admin@tenant-a.com',
            'password': 'pass123',
            'tenant': 'tenant-a'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['tenant']['subdomain'], 'tenant-a')
    
    def test_login_with_wrong_tenant_fails(self):
        """Login con email correcto pero tenant incorrecto debe fallar"""
        response = self.client.post('/api/auth/login/', {
            'email': 'admin@tenant-a.com',
            'password': 'pass123',
            'tenant_subdomain': 'tenant-b'  # ⚠️ Tenant incorrecto
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('Credenciales inválidas', str(response.data))
    
    def test_login_with_correct_tenant_succeeds(self):
        """Login con tenant correcto debe funcionar"""
        response = self.client.post('/api/auth/login/', {
            'email': 'admin@tenant-a.com',
            'password': 'pass123',
            'tenant_subdomain': 'tenant-a'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('tenant', response.data)
        self.assertEqual(response.data['tenant']['subdomain'], 'tenant-a')
    
    def test_same_email_different_tenants_isolated_login(self):
        """Mismo email en diferentes tenants debe tener login aislado"""
        # Crear usuario con mismo email en tenant B
        User.objects.create_user(
            email='staff@tenant-a.com',  # Mismo email que staff_a
            password='different_pass',
            full_name='Staff Tenant B',
            tenant=self.tenant_b,
            role='Client-Staff'
        )
        
        # Login en tenant A
        response_a = self.client.post('/api/auth/login/', {
            'email': 'staff@tenant-a.com',
            'password': 'pass123',
            'tenant_subdomain': 'tenant-a'
        })
        self.assertEqual(response_a.status_code, 200)
        
        # Login en tenant B con password diferente
        response_b = self.client.post('/api/auth/login/', {
            'email': 'staff@tenant-a.com',
            'password': 'different_pass',
            'tenant_subdomain': 'tenant-b'
        })
        self.assertEqual(response_b.status_code, 200)
        
        # Verificar que son usuarios diferentes
        self.assertNotEqual(
            response_a.data['user']['id'],
            response_b.data['user']['id']
        )
    
    def test_client_admin_cannot_create_superadmin(self):
        """ClientAdmin no puede crear SuperAdmin"""
        self.client.force_authenticate(user=self.admin_a)
        response = self.client.post('/api/auth/users/', {
            'email': 'hacker@tenant-a.com',
            'full_name': 'Hacker',
            'password': 'pass123',
            'role': 'SuperAdmin'  # ⚠️ Intento de escalada
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn('no puede asignar rol SuperAdmin', str(response.data))
    
    def test_client_admin_can_create_staff(self):
        """ClientAdmin puede crear Client-Staff"""
        self.client.force_authenticate(user=self.admin_a)
        response = self.client.post('/api/auth/users/', {
            'email': 'newstaff@tenant-a.com',
            'full_name': 'New Staff',
            'password': 'pass123',
            'role': 'Client-Staff'
        })
        self.assertEqual(response.status_code, 201)
        
        # Verificar que se creó en el tenant correcto
        new_user = User.objects.get(email='newstaff@tenant-a.com')
        self.assertEqual(new_user.tenant, self.tenant_a)
        self.assertEqual(new_user.role, 'Client-Staff')
    
    def test_cannot_access_other_tenant_users(self):
        """Usuario no puede acceder a usuarios de otro tenant"""
        self.client.force_authenticate(user=self.admin_a)
        
        # Intentar acceder a usuario de tenant B
        response = self.client.get(f'/api/auth/users/{self.admin_b.id}/')
        self.assertEqual(response.status_code, 404)
    
    def test_cannot_modify_user_from_other_tenant(self):
        """Usuario no puede modificar usuarios de otro tenant"""
        self.client.force_authenticate(user=self.admin_a)
        
        # Intentar modificar usuario de tenant B
        response = self.client.patch(f'/api/auth/users/{self.admin_b.id}/', {
            'full_name': 'Hacked Name'
        })
        self.assertEqual(response.status_code, 404)
    
    def test_staff_cannot_create_users(self):
        """Client-Staff no puede crear usuarios"""
        self.client.force_authenticate(user=self.staff_a)
        response = self.client.post('/api/auth/users/', {
            'email': 'unauthorized@tenant-a.com',
            'full_name': 'Unauthorized',
            'password': 'pass123',
            'role': 'Client-Staff'
        })
        self.assertEqual(response.status_code, 403)
    
    def test_jwt_contains_tenant_id(self):
        """JWT debe contener tenant_id en claims"""
        response = self.client.post('/api/auth/login/', {
            'email': 'admin@tenant-a.com',
            'password': 'pass123',
            'tenant_subdomain': 'tenant-a'
        })
        self.assertEqual(response.status_code, 200)
        
        # Decodificar JWT y verificar claims
        import jwt
        from django.conf import settings
        token = response.data['access']
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        
        self.assertIn('tenant_id', decoded)
        self.assertEqual(decoded['tenant_id'], self.tenant_a.id)
        self.assertEqual(decoded['tenant_subdomain'], 'tenant-a')


class RoleHierarchyTests(TestCase):
    """Tests de jerarquía de roles"""
    
    def setUp(self):
        self.owner = User.objects.create_superuser(
            email='role-owner@example.com',
            password='pass123',
            full_name='Role Test Owner',
            role='SuperAdmin'
        )
        settings = SystemSettings.get_settings()
        settings.require_email_verification = False
        settings.enable_mfa = False
        settings.save(update_fields=['require_email_verification', 'enable_mfa'])
        self.plan = SubscriptionPlan.objects.create(name='test', price=0, max_users=10)
        self.tenant = Tenant.objects.create(
            name='Test Tenant',
            subdomain='test',
            subscription_plan=self.plan,
            owner=self.owner
        )
        
        self.superadmin = User.objects.create_user(
            email='super@admin.com',
            password='pass123',
            full_name='Super Admin',
            is_superuser=True,
            role='SuperAdmin'
        )
        self.client_admin = User.objects.create_user(
            email='admin@test.com',
            password='pass123',
            full_name='Client Admin',
            tenant=self.tenant,
            role='Client-Admin'
        )
        self.staff = User.objects.create_user(
            email='staff@test.com',
            password='pass123',
            full_name='Client Staff',
            tenant=self.tenant,
            role='Client-Staff'
        )
        
        self.client = APIClient()
    
    def test_superadmin_can_create_any_role(self):
        """SuperAdmin puede crear cualquier rol"""
        self.client.force_authenticate(user=self.superadmin)
        
        roles = ['SuperAdmin', 'Client-Admin', 'Client-Staff']
        for role in roles:
            response = self.client.post('/api/auth/users/', {
                'email': f'{role.lower()}@test.com',
                'full_name': f'Test {role}',
                'password': 'pass123',
                'role': role,
                'tenant': self.tenant.id if role != 'SuperAdmin' else None
            })
            self.assertIn(response.status_code, [200, 201], 
                         f'SuperAdmin should create {role}')
    
    def test_client_admin_cannot_create_client_admin(self):
        """ClientAdmin no puede crear otro ClientAdmin"""
        self.client.force_authenticate(user=self.client_admin)
        response = self.client.post('/api/auth/users/', {
            'email': 'another-admin@test.com',
            'full_name': 'Another Admin',
            'password': 'pass123',
            'role': 'Client-Admin'
        })
        self.assertEqual(response.status_code, 403)
    
    def test_client_admin_can_create_staff_roles(self):
        """ClientAdmin puede crear roles de staff"""
        self.client.force_authenticate(user=self.client_admin)
        
        staff_roles = ['Client-Staff', 'Estilista', 'Cajera', 'Manager']
        for role in staff_roles:
            response = self.client.post('/api/auth/users/', {
                'email': f'{role.lower()}@test.com',
                'full_name': f'Test {role}',
                'password': 'pass123',
                'role': role
            })
            self.assertEqual(response.status_code, 201,
                           f'ClientAdmin should create {role}')
    
    def test_staff_cannot_modify_admin(self):
        """Staff no puede modificar Admin"""
        self.client.force_authenticate(user=self.staff)
        response = self.client.patch(f'/api/auth/users/{self.client_admin.id}/', {
            'full_name': 'Hacked'
        })
        self.assertEqual(response.status_code, 403)


if __name__ == '__main__':
    import django
    django.setup()
    from django.test.utils import get_runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['apps.auth_api.tests_security'])
