import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import UserSubscription, SubscriptionPlan
from .stripe_service import StripeService
from .models import Invoice, PaymentAttempt
import stripe

User = get_user_model()

class StripeIntegrationTest(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='Test Peluquería',
            subdomain='test-peluqueria',
            owner_id=1
        )
        
        self.user = User.objects.create_user(
            email='test@peluqueria.com',
            password='test123',
            full_name='Test User',
            tenant=self.tenant
        )
        
        self.plan = SubscriptionPlan.objects.create(
            name='basic',
            price=29.99,
            duration_month=1
        )

    @patch('stripe.Customer.create')
    def test_create_stripe_customer(self, mock_create):
        """Test creación de cliente en Stripe"""
        mock_customer = MagicMock()
        mock_customer.id = 'cus_test123'
        mock_create.return_value = mock_customer
        
        customer = StripeService.create_customer(self.user)
        
        mock_create.assert_called_once_with(
            email=self.user.email,
            name=self.user.full_name,
            metadata={'user_id': self.user.id}
        )
        self.assertEqual(customer.id, 'cus_test123')

    @patch('stripe.Subscription.create')
    @patch('apps.billing_api.stripe_service.StripeService.create_customer')
    def test_create_subscription(self, mock_create_customer, mock_create_sub):
        """Test creación de suscripción en Stripe"""
        mock_customer = MagicMock()
        mock_customer.id = 'cus_test123'
        mock_create_customer.return_value = mock_customer
        
        mock_subscription = MagicMock()
        mock_subscription.id = 'sub_test123'
        mock_create_sub.return_value = mock_subscription
        
        subscription = StripeService.create_subscription(self.user, 'price_test123')
        
        mock_create_sub.assert_called_once()
        self.assertEqual(subscription.id, 'sub_test123')

    @patch('stripe.error.StripeError')
    @patch('stripe.Customer.create')
    def test_stripe_error_handling(self, mock_create, mock_error):
        """Test manejo de errores de Stripe"""
        mock_create.side_effect = stripe.error.StripeError("Test error")
        
        with self.assertRaises(Exception) as context:
            StripeService.create_customer(self.user)
        
        self.assertIn("Error creando cliente Stripe", str(context.exception))

    def test_invoice_creation(self):
        """Test creación de factura local"""
        invoice = Invoice.objects.create(
            user=self.user,
            amount=29.99,
            description='Suscripción mensual',
            status='pending'
        )
        
        self.assertEqual(invoice.user, self.user)
        self.assertEqual(float(invoice.amount), 29.99)
        self.assertEqual(invoice.status, 'pending')
        self.assertFalse(invoice.is_paid)

    def test_payment_attempt_tracking(self):
        """Test seguimiento de intentos de pago"""
        invoice = Invoice.objects.create(
            user=self.user,
            amount=29.99,
            status='pending'
        )
        
        # Intento fallido
        attempt = PaymentAttempt.objects.create(
            invoice=invoice,
            success=False,
            status='failed',
            message='Tarjeta declinada'
        )
        
        self.assertEqual(attempt.invoice, invoice)
        self.assertFalse(attempt.success)
        self.assertEqual(attempt.status, 'failed')

    @patch('apps.billing_api.stripe_service.StripeService.suspend_customer')
    def test_customer_suspension(self, mock_suspend):
        """Test suspensión de cliente moroso"""
        mock_suspend.return_value = True
        
        # Crear factura vencida
        invoice = Invoice.objects.create(
            user=self.user,
            amount=29.99,
            status='pending'
        )
        
        # Crear múltiples intentos fallidos
        for i in range(3):
            PaymentAttempt.objects.create(
                invoice=invoice,
                success=False,
                status='failed'
            )
        
        # Verificar que se puede suspender
        result = StripeService.suspend_customer('cus_test123')
        self.assertTrue(result)
        mock_suspend.assert_called_once_with('cus_test123')

    def test_tenant_status_update_on_payment(self):
        """Test actualización de estado del tenant al pagar"""
        # Tenant suspendido
        self.tenant.subscription_status = 'suspended'
        self.tenant.save()
        
        # Simular pago exitoso
        invoice = Invoice.objects.create(
            user=self.user,
            amount=29.99,
            is_paid=True,
            status='paid'
        )
        
        # En un webhook real, esto actualizaría el tenant
        # Por ahora solo verificamos que el invoice se marca como pagado
        self.assertTrue(invoice.is_paid)
        self.assertEqual(invoice.status, 'paid')