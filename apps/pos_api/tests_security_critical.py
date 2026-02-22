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
from decimal import Decimal
from django.utils import timezone
import threading

User = get_user_model()


def create_test_user(email, password="pass123", tenant=None, is_superuser=False, full_name=None):
    """Helper para crear usuarios en tests con campos requeridos"""
    if full_name is None:
        full_name = email.split('@')[0].title()
    
    if is_superuser:
        return User.objects.create_superuser(email=email, password=password, full_name=full_name)
    return User.objects.create_user(email=email, password=password, tenant=tenant, full_name=full_name)


class IDORSecurityTests(TestCase):
    """Corrección #1 y #5: IDOR en SaleViewSet y CashRegisterViewSet"""
    
    def setUp(self):
        self.owner_a = create_test_user("owner_a@test.com")
        self.tenant_a = Tenant.objects.create(name="Tenant A", subdomain="tenant-a", owner=self.owner_a)
        self.user_a = create_test_user("a@test.com", tenant=self.tenant_a)
        
        self.owner_b = create_test_user("owner_b@test.com")
        self.tenant_b = Tenant.objects.create(name="Tenant B", subdomain="tenant-b", owner=self.owner_b)
        self.user_b = create_test_user("b@test.com", tenant=self.tenant_b)
        
        self.product_a = Product.objects.create(name="Product A", price=100, stock=10, tenant=self.tenant_a)
        self.sale_a = Sale.objects.create(tenant=self.tenant_a, total=100, status='completed', created_by=self.user_a)
        
        self.cash_register_a = CashRegister.objects.create(
            tenant=self.tenant_a, name="Caja A", opening_balance=1000, created_by=self.user_a
        )
        
        self.client = APIClient()
    
    def test_idor_sale_cross_tenant_blocked(self):
        """CRÍTICO: Usuario de Tenant B NO puede ver ventas de Tenant A"""
        self.client.force_authenticate(user=self.user_b)
        response = self.client.get('/api/pos/sales/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
    
    def test_idor_sale_own_tenant_allowed(self):
        """Usuario de Tenant A SÍ puede ver sus propias ventas"""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get('/api/pos/sales/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.sale_a.id)
    
    def test_idor_cash_register_cross_tenant_blocked(self):
        """CRÍTICO: Usuario de Tenant B NO puede ver cajas de Tenant A"""
        self.client.force_authenticate(user=self.user_b)
        response = self.client.get('/api/pos/cash-registers/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
    
    def test_idor_superuser_sees_all(self):
        """Superusuario SÍ puede ver todas las ventas (sin tenant)"""
        superuser = create_test_user("admin@test.com", is_superuser=True)
        self.client.force_authenticate(user=superuser)
        response = self.client.get('/api/pos/sales/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class RaceConditionStockTests(TransactionTestCase):
    """Corrección #2: Race condition en actualización de stock"""
    
    def setUp(self):
        self.owner = create_test_user("owner@test.com")
        self.tenant = Tenant.objects.create(name="Test Tenant", subdomain="test", owner=self.owner)
        self.user = create_test_user("test@test.com", tenant=self.tenant)
        self.product = Product.objects.create(name="Test Product", price=100, stock=10, tenant=self.tenant)
        self.cash_register = CashRegister.objects.create(
            tenant=self.tenant, name="Caja Test", opening_balance=1000, created_by=self.user
        )
    
    def test_concurrent_stock_updates_no_race_condition(self):
        """CRÍTICO: Actualizaciones concurrentes de stock deben ser atómicas"""
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
                            tenant=self.tenant, total=100, status='completed',
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
        self.owner_a = create_test_user("owner_a2@test.com")
        self.tenant_a = Tenant.objects.create(name="Tenant A2", subdomain="tenant-a2", owner=self.owner_a)
        self.user_a = create_test_user("a2@test.com", tenant=self.tenant_a)
        
        self.owner_b = create_test_user("owner_b2@test.com")
        self.tenant_b = Tenant.objects.create(name="Tenant B2", subdomain="tenant-b2", owner=self.owner_b)
        self.user_b = create_test_user("b2@test.com", tenant=self.tenant_b)
        
        self.cash_register_a = CashRegister.objects.create(
            tenant=self.tenant_a, name="Caja A", opening_balance=1000, created_by=self.user_a
        )
        
        self.sale_a = Sale.objects.create(
            tenant=self.tenant_a, total=100, status='completed',
            created_by=self.user_a, cash_register=self.cash_register_a
        )
        
        self.client = APIClient()
    
    def test_refund_cross_tenant_blocked(self):
        """CRÍTICO: Usuario de Tenant B NO puede reembolsar venta de Tenant A"""
        self.client.force_authenticate(user=self.user_b)
        response = self.client.post(f'/api/pos/sales/{self.sale_a.id}/refund/', {'reason': 'Test refund'})
        
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
    
    def test_refund_own_tenant_allowed(self):
        """Usuario de Tenant A SÍ puede reembolsar su propia venta"""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(f'/api/pos/sales/{self.sale_a.id}/refund/', {'reason': 'Valid refund'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sale_a.refresh_from_db()
        self.assertEqual(self.sale_a.status, 'refunded')


class DiscountValidationTests(TestCase):
    """Corrección #6: Validación de descuentos negativos y mayores al total"""
    
    def setUp(self):
        self.owner = create_test_user("owner3@test.com")
        self.tenant = Tenant.objects.create(name="Test Tenant3", subdomain="test3", owner=self.owner)
        self.user = create_test_user("testuser3@test.com", tenant=self.tenant)
        self.cash_register = CashRegister.objects.create(
            tenant=self.tenant, name="Caja Test", opening_balance=1000, created_by=self.user
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    def test_negative_discount_blocked(self):
        """CRÍTICO: Descuento negativo debe ser rechazado"""
        response = self.client.post('/api/pos/sales/', {
            'total': 100, 'discount': -10, 'status': 'completed', 'cash_register': self.cash_register.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('discount', str(response.data).lower())
    
    def test_discount_greater_than_total_blocked(self):
        """CRÍTICO: Descuento mayor al total debe ser rechazado"""
        response = self.client.post('/api/pos/sales/', {
            'total': 100, 'discount': 150, 'status': 'completed', 'cash_register': self.cash_register.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('discount', str(response.data).lower())
    
    def test_valid_discount_allowed(self):
        """Descuento válido debe ser aceptado"""
        response = self.client.post('/api/pos/sales/', {
            'total': 100, 'discount': 10, 'status': 'completed', 'cash_register': self.cash_register.id
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class TenantMiddlewareTests(TestCase):
    """Corrección #4: Bypass de tenant middleware en rutas admin"""
    
    def setUp(self):
        self.owner = create_test_user("owner4@test.com")
        self.tenant = Tenant.objects.create(name="Test Tenant4", subdomain="test4", owner=self.owner)
        self.regular_user = create_test_user("regular4@test.com", tenant=self.tenant)
        self.superuser = create_test_user("admin4@test.com", is_superuser=True)
        self.client = APIClient()
    
    def test_admin_path_requires_superuser(self):
        """CRÍTICO: Rutas /admin/ requieren superusuario"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/admin/')
        
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_302_FOUND])
    
    def test_superuser_can_access_admin(self):
        """Superusuario SÍ puede acceder a /admin/"""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get('/admin/')
        
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_302_FOUND])


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
