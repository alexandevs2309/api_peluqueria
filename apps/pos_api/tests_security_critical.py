"""
Tests de Seguridad Críticos - Validación de 8 Correcciones Aplicadas
Valida: IDOR, Race Conditions, Tenant Isolation, Discount Validation
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.tenants_api.models import Tenant
from apps.pos_api.models import Sale, Product, CashRegister
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
import threading

User = get_user_model()


def authenticate_client(client, user):
    client.force_authenticate(user=user)
    if user:
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken.for_user(user)
        if getattr(user, 'tenant_id', None):
            token['tenant_id'] = user.tenant_id
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")
        client.cookies['access_token'] = str(token)
    else:
        client.credentials()
        client.cookies.clear()


def _setup_rbac(user, tenant):
    from apps.roles_api.models import Role, UserRole
    from django.contrib.auth.models import Permission

    role, _ = Role.objects.get_or_create(name='TestRole', defaults={'description': 'Test role'})
    perms = Permission.objects.filter(content_type__app_label='pos_api')
    role.permissions.add(*perms)
    UserRole.objects.get_or_create(user=user, role=role, tenant=tenant)


def _setup_plan(tenant):
    from apps.subscriptions_api.models import SubscriptionPlan

    plan, created = SubscriptionPlan.objects.get_or_create(
        name='basic',
        defaults={
            'price': 0, 'max_users': 10, 'max_employees': 10,
            'features': {'cash_register': True},
        }
    )
    if not created:
        plan.features = {'cash_register': True}
        plan.max_users = 10
        plan.max_employees = 10
        plan.save(update_fields=['features', 'max_users', 'max_employees'])
    tenant.subscription_plan = plan
    tenant.save(update_fields=['subscription_plan'])


def create_test_user(email, password="pass1234", tenant=None, is_superuser=False, full_name=None):
    """Helper para crear usuarios en tests con campos requeridos"""
    if full_name is None:
        full_name = email.split('@')[0].title()
    
    if is_superuser:
        return User.objects.create_superuser(email=email, password=password, full_name=full_name)
    return User.objects.create_user(email=email, password=password, tenant=tenant, full_name=full_name)


class IDORSecurityTests(TestCase):
    """Corrección #1 y #5: IDOR en SaleViewSet y CashRegisterViewSet"""
    
    def setUp(self):
        self.owner_a = create_test_user("owner_a@test.com", is_superuser=True)
        self.tenant_a = Tenant.objects.create(name="Tenant A", subdomain="tenant-a", owner=self.owner_a)
        self.user_a = create_test_user("a@test.com", tenant=self.tenant_a)
        _setup_plan(self.tenant_a)
        _setup_rbac(self.user_a, self.tenant_a)
        
        self.owner_b = create_test_user("owner_b@test.com", is_superuser=True)
        self.tenant_b = Tenant.objects.create(name="Tenant B", subdomain="tenant-b", owner=self.owner_b)
        self.user_b = create_test_user("b@test.com", tenant=self.tenant_b)
        _setup_plan(self.tenant_b)
        _setup_rbac(self.user_b, self.tenant_b)
        
        self.product_a = Product.objects.create(name="Product A", price=100, stock=10, tenant=self.tenant_a)
        self.sale_a = Sale.objects.create(tenant=self.tenant_a, total=100, status='confirmed', created_by=self.user_a, user=self.user_a)
        
        self.cash_register_a = CashRegister.objects.create(
            tenant=self.tenant_a, user=self.user_a, initial_cash=1000
        )
        
        self.client = APIClient()
    
    def test_idor_sale_cross_tenant_blocked(self):
        """CRÍTICO: Usuario de Tenant B NO puede ver ventas de Tenant A"""
        authenticate_client(self.client, self.user_b)
        response = self.client.get('/api/pos/sales/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
    
    def test_idor_sale_own_tenant_allowed(self):
        """Usuario de Tenant A SÍ puede ver sus propias ventas"""
        authenticate_client(self.client, self.user_a)
        response = self.client.get('/api/pos/sales/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.sale_a.id)
    
    def test_idor_cash_register_cross_tenant_blocked(self):
        """CRÍTICO: Usuario de Tenant B NO puede ver cajas de Tenant A"""
        authenticate_client(self.client, self.user_b)
        response = self.client.get('/api/pos/cashregisters/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
    
    def test_idor_superuser_sees_all(self):
        """Superusuario SÍ puede ver todas las ventas (sin tenant)"""
        superuser = create_test_user("admin@test.com", is_superuser=True)
        authenticate_client(self.client, superuser)
        response = self.client.get('/api/pos/sales/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class RaceConditionStockTests(TransactionTestCase):
    """Corrección #2: Race condition en actualización de stock"""
    
    def setUp(self):
        self.owner = create_test_user("owner@test.com", is_superuser=True)
        self.tenant = Tenant.objects.create(name="Test Tenant", subdomain="test", owner=self.owner)
        self.user = create_test_user("test@test.com", tenant=self.tenant)
        _setup_plan(self.tenant)
        _setup_rbac(self.user, self.tenant)
        self.product = Product.objects.create(name="Test Product", price=100, stock=10, tenant=self.tenant)
        self.cash_register = CashRegister.objects.create(
            tenant=self.tenant, user=self.user, initial_cash=1000
        )
    
    def test_concurrent_stock_updates_no_race_condition(self):
        """CRÍTICO: Actualizaciones concurrentes de stock deben ser atómicas"""
        from django.db import connection
        if connection.vendor == 'sqlite':
            self.skipTest("SQLite no soporta select_for_update concurrente real")
        initial_stock = self.product.stock
        errors = []
        
        def create_sale():
            try:
                from django.db import transaction
                with transaction.atomic():
                    product = Product.objects.select_for_update().get(id=self.product.id)
                    if product.stock >= 1:
                        product.stock -= 1
                        product.save()
                        Sale.objects.create(
                            tenant=self.tenant, total=100, status='confirmed',
                            created_by=self.user, cash_register=self.cash_register
                        )
            except Exception as e:
                errors.append(str(e))
        
        threads = [threading.Thread(target=create_sale) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.product.refresh_from_db()
        expected_stock = initial_stock - 5
        self.assertEqual(self.product.stock, expected_stock)
        self.assertEqual(len(errors), 0)


class RefundTenantValidationTests(TestCase):
    """Corrección #3: IDOR en refund sin validación de tenant"""
    
    def setUp(self):
        self.owner_a = create_test_user("owner_a2@test.com", is_superuser=True)
        self.tenant_a = Tenant.objects.create(name="Tenant A2", subdomain="tenant-a2", owner=self.owner_a)
        self.user_a = create_test_user("a2@test.com", tenant=self.tenant_a)
        _setup_plan(self.tenant_a)
        _setup_rbac(self.user_a, self.tenant_a)
        
        self.owner_b = create_test_user("owner_b2@test.com", is_superuser=True)
        self.tenant_b = Tenant.objects.create(name="Tenant B2", subdomain="tenant-b2", owner=self.owner_b)
        self.user_b = create_test_user("b2@test.com", tenant=self.tenant_b)
        _setup_plan(self.tenant_b)
        _setup_rbac(self.user_b, self.tenant_b)
        
        self.cash_register_a = CashRegister.objects.create(
            tenant=self.tenant_a, user=self.user_a, initial_cash=1000
        )
        
        self.sale_a = Sale.objects.create(
            tenant=self.tenant_a, total=100, status='confirmed',
            created_by=self.user_a, user=self.user_a, cash_register=self.cash_register_a
        )
        from django.contrib.contenttypes.models import ContentType
        from apps.pos_api.models import SaleDetail
        product_ct = ContentType.objects.get(app_label='inventory_api', model='product')
        SaleDetail.objects.create(
            sale=self.sale_a, content_type=product_ct, object_id=1,
            name='Test Product', quantity=1, price=100
        )
        
        self.client = APIClient()
    
    def test_refund_cross_tenant_blocked(self):
        """CRÍTICO: Usuario de Tenant B NO puede reembolsar venta de Tenant A"""
        authenticate_client(self.client, self.user_b)
        response = self.client.post(f'/api/pos/sales/{self.sale_a.id}/refund/', {'reason': 'Test refund cross tenant'}, format='json')
        
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
    
    def test_refund_own_tenant_allowed(self):
        """Usuario de Tenant A SÍ puede reembolsar su propia venta"""
        authenticate_client(self.client, self.user_a)
        response = self.client.post(f'/api/pos/sales/{self.sale_a.id}/refund/', {'reason': 'Valid refund long enough'}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sale_a.refresh_from_db()
        self.assertEqual(self.sale_a.status, 'refunded')


class DiscountValidationTests(TestCase):
    """Corrección #6: Validación de descuentos negativos y mayores al total"""
    
    def setUp(self):
        self.owner = create_test_user("owner3@test.com", is_superuser=True)
        self.tenant = Tenant.objects.create(name="Test Tenant3", subdomain="test3", owner=self.owner)
        self.user = create_test_user("testuser3@test.com", tenant=self.tenant)
        _setup_plan(self.tenant)
        _setup_rbac(self.user, self.tenant)
        self.cash_register = CashRegister.objects.create(
            tenant=self.tenant, user=self.user, initial_cash=1000
        )
        self.client = APIClient()
        authenticate_client(self.client, self.user)
    
    def _sale_data(self, **overrides):
        data = {
            'total': 100, 'discount': 0, 'status': 'confirmed',
            'cash_register': self.cash_register.id,
            'details': [{'content_type': 'service', 'object_id': 1, 'quantity': 1, 'price': 100, 'name': 'Service 1'}],
            'payments': [{'amount': 100, 'method': 'cash'}],
        }
        data.update(overrides)
        return data

    def test_negative_discount_blocked(self):
        """CRÍTICO: Descuento negativo debe ser rechazado"""
        response = self.client.post('/api/pos/sales/', self._sale_data(discount=-10), format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any('negativo' in str(v).lower() for v in response.data.values()) if isinstance(response.data, dict) else 'negativo' in str(response.data).lower())
    
    def test_discount_greater_than_total_blocked(self):
        """CRÍTICO: Descuento mayor al total debe ser rechazado"""
        response = self.client.post('/api/pos/sales/', self._sale_data(discount=150), format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(any('mayor' in str(v).lower() for v in response.data.values()) if isinstance(response.data, dict) else 'mayor' in str(response.data).lower())
    
    def test_valid_discount_allowed(self):
        """Descuento válido debe ser aceptado"""
        response = self.client.post('/api/pos/sales/', self._sale_data(discount=10), format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class TenantMiddlewareTests(TestCase):
    """Corrección #4: Bypass de tenant middleware en rutas admin"""
    
    def setUp(self):
        self.owner = create_test_user("owner4@test.com", is_superuser=True)
        self.tenant = Tenant.objects.create(name="Test Tenant4", subdomain="test4", owner=self.owner)
        self.regular_user = create_test_user("regular4@test.com", tenant=self.tenant)
        self.superuser = create_test_user("admin4@test.com", is_superuser=True)
        _setup_plan(self.tenant)
        _setup_rbac(self.regular_user, self.tenant)
        self.client = APIClient()
    
    def test_admin_path_requires_superuser(self):
        """CRÍTICO: Rutas /admin/ requieren superusuario"""
        authenticate_client(self.client, self.regular_user)
        response = self.client.get('/admin/')
        
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_302_FOUND])
    
    def test_superuser_can_access_admin(self):
        """Superusuario SÍ puede acceder a /admin/"""
        authenticate_client(self.client, self.superuser)
        response = self.client.get('/admin/')
        
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_302_FOUND])

    def test_paywall_safe_endpoints_remain_available_for_suspended_tenant(self):
        """Tenant suspendido puede cargar contexto minimo para pantalla de pago"""
        self.tenant.subscription_status = 'suspended'
        self.tenant.is_active = False
        self.tenant.access_until = timezone.now() - timedelta(days=10)
        self.tenant.save(update_fields=['subscription_status', 'is_active', 'access_until', 'updated_at'])

        authenticate_client(self.client, self.regular_user)

        locale_response = self.client.get('/api/tenants/locale/')
        current_response = self.client.get('/api/tenants/current/')
        entitlements_response = self.client.get('/api/subscriptions/me/entitlements/')

        self.assertEqual(locale_response.status_code, status.HTTP_200_OK)
        self.assertEqual(current_response.status_code, status.HTTP_200_OK)
        self.assertEqual(entitlements_response.status_code, status.HTTP_200_OK)

    def test_operational_endpoints_still_blocked_for_suspended_tenant(self):
        """Tenant suspendido no puede seguir usando modulos operativos"""
        self.tenant.subscription_status = 'suspended'
        self.tenant.is_active = False
        self.tenant.access_until = timezone.now() - timedelta(days=10)
        self.tenant.save(update_fields=['subscription_status', 'is_active', 'access_until', 'updated_at'])

        authenticate_client(self.client, self.regular_user)
        response = self.client.get('/api/appointments/appointments/')

        self.assertIn(response.status_code, [status.HTTP_402_PAYMENT_REQUIRED, status.HTTP_403_FORBIDDEN])


class StripeWebhookSecurityTests(TestCase):
    """Corrección #8: Validación de firma Stripe en webhooks"""
    
    def setUp(self):
        self.client = APIClient()
    
    def test_webhook_without_signature_rejected(self):
        """CRÍTICO: Webhook sin firma debe ser rechazado"""
        response = self.client.post(
            '/api/billing/webhooks/stripe/',
            data={'type': 'invoice.payment_succeeded'},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_webhook_with_invalid_signature_rejected(self):
        """CRÍTICO: Webhook con firma inválida debe ser rechazado"""
        response = self.client.post(
            '/api/billing/webhooks/stripe/',
            data={'type': 'invoice.payment_succeeded'},
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='invalid_signature'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CSRFCookieSecurityTests(TestCase):
    """Corrección #7: Configuración SameSite en cookies CSRF"""
    
    def test_csrf_cookie_samesite_configured(self):
        """CRÍTICO: Cookies CSRF deben tener SameSite configurado"""
        from django.conf import settings
        
        self.assertIn(settings.SESSION_COOKIE_SAMESITE, ['Lax', 'Strict'])
        self.assertIn(settings.CSRF_COOKIE_SAMESITE, ['Lax', 'Strict'])
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
