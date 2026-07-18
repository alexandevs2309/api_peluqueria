import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from django.urls import reverse
from unittest.mock import patch, MagicMock
from apps.auth_api.factories import UserFactory
from apps.payments_api.models import Payment, PaymentProvider, WebhookEvent
from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription


@pytest.fixture
def payment_provider():
    provider, _ = PaymentProvider.objects.get_or_create(
        name='stripe',
        defaults={'is_active': True}
    )
    return provider


@pytest.fixture
def subscription_plan():
    return SubscriptionPlan.objects.create(
        name='basic',
        price=Decimal('29.99'),
        is_active=True
    )


@pytest.fixture
def payment(payment_provider):
    user = UserFactory()
    return Payment.objects.create(
        user=user,
        provider=payment_provider,
        amount=Decimal('29.99'),
        status='pending',
        currency='USD'
    )


@pytest.mark.django_db
class TestPaymentModel:
    def test_create_payment(self, payment_provider):
        user = UserFactory()
        p = Payment.objects.create(
            user=user,
            provider=payment_provider,
            amount=Decimal('100.00'),
            status='pending'
        )
        assert p.id is not None
        assert p.status == 'pending'
        assert str(p).startswith('Payment')

    def test_payment_status_choices(self, payment_provider):
        user = UserFactory()
        for status_val in ['pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded']:
            p = Payment.objects.create(
                user=user, provider=payment_provider,
                amount=Decimal('50.00'), status=status_val
            )
            assert p.status == status_val

    def test_payment_str(self, payment):
        assert payment.user.email in str(payment)
        assert payment.status in str(payment)


@pytest.mark.django_db
class TestPaymentProviderModel:
    def test_encrypts_api_key_on_save(self):
        provider = PaymentProvider.objects.create(
            name='paypal',
            api_key='sk_test_secret_key_12345',
            is_active=True
        )
        assert provider.api_key != 'sk_test_secret_key_12345'
        assert provider.get_api_key() == 'sk_test_secret_key_12345'

    def test_encrypts_webhook_secret_on_save(self):
        provider = PaymentProvider.objects.create(
            name='manual',
            webhook_secret='whsec_secret_12345',
            is_active=True
        )
        assert provider.webhook_secret != 'whsec_secret_12345'
        assert provider.get_webhook_secret() == 'whsec_secret_12345'


@pytest.mark.django_db
class TestWebhookEventModel:
    def test_create_webhook_event(self, payment_provider):
        event = WebhookEvent.objects.create(
            provider=payment_provider,
            event_id='evt_12345',
            event_type='payment_intent.succeeded',
            data={'amount': 2999}
        )
        assert event.id is not None
        assert event.processed is False
        assert str(event) == f'stripe - payment_intent.succeeded - evt_12345'

    def test_webhook_event_unique_event_id(self, payment_provider):
        WebhookEvent.objects.create(
            provider=payment_provider,
            event_id='evt_unique',
            event_type='test',
            data={}
        )
        with pytest.raises(Exception):
            WebhookEvent.objects.create(
                provider=payment_provider,
                event_id='evt_unique',
                event_type='test',
                data={}
            )


@pytest.mark.django_db
class TestPaymentAPI:
    def test_list_payments_requires_auth(self, api_client):
        url = reverse('payment-list')
        response = api_client.get(url)
        assert response.status_code in [401, 403]

    def test_create_payment_returns_405(self, authorized_user, payment_provider):
        user, client = authorized_user
        url = reverse('payment-list')
        data = {'amount': '50.00', 'provider': payment_provider.id}
        response = client.post(url, data)
        assert response.status_code == 405
        assert 'Direct payment creation is disabled' in str(response.data)

    def test_update_payment_returns_405(self, authorized_user, payment_provider):
        user, client = authorized_user
        payment = Payment.objects.create(user=user, provider=payment_provider, amount=Decimal('29.99'))
        url = reverse('payment-detail', args=[payment.id])
        response = client.patch(url, {'status': 'completed'})
        assert response.status_code == 405
        assert 'Direct payment mutation is disabled' in str(response.data)

    def test_delete_payment_returns_405(self, authorized_user, payment_provider):
        user, client = authorized_user
        payment = Payment.objects.create(user=user, provider=payment_provider, amount=Decimal('29.99'))
        url = reverse('payment-detail', args=[payment.id])
        response = client.delete(url)
        assert response.status_code == 405
        assert 'Direct payment deletion is disabled' in str(response.data)

    def test_retrieve_payment(self, authorized_user, payment_provider):
        user, client = authorized_user
        payment = Payment.objects.create(user=user, provider=payment_provider, amount=Decimal('29.99'), tenant=user.tenant)
        url = reverse('payment-detail', args=[payment.id])
        response = client.get(url)
        assert response.status_code == 200
        assert 'amount' in response.data


@pytest.mark.django_db
class TestStripeService:
    def test_stripe_service_init_no_library(self):
        with patch('apps.payments_api.services.stripe', None):
            with pytest.raises(Exception, match='Stripe library not installed'):
                from apps.payments_api.services import StripeService
                StripeService()

    def test_create_customer(self, payment_provider):
        with patch('apps.payments_api.services.stripe') as mock_stripe:
            mock_stripe.Customer.create.return_value = MagicMock(id='cus_test123')
            from apps.payments_api.services import StripeService
            service = StripeService()
            user = UserFactory()
            customer = service.create_customer(user)
            assert customer.id == 'cus_test123'
            mock_stripe.Customer.create.assert_called_once()

    def test_create_subscription_payment(self, payment_provider, subscription_plan):
        import stripe as real_stripe
        with patch('apps.payments_api.services.stripe') as mock_stripe:
            mock_stripe.Customer.create.return_value = MagicMock(id='cus_test123')
            mock_stripe.PaymentIntent.create.return_value = MagicMock(
                id='pi_test123', client_secret='secret_test123'
            )
            from apps.payments_api.services import StripeService
            service = StripeService()
            user = UserFactory()
            result = service.create_subscription_payment(user, subscription_plan.id)
            assert 'payment_id' in result
            assert 'client_secret' in result


@pytest.mark.django_db
class TestOnboardingService:
    def test_complete_subscription_purchase_invalid_payment(self):
        from apps.payments_api.services import OnboardingService
        with pytest.raises(Exception, match='Error completing onboarding'):
            OnboardingService.complete_subscription_purchase(99999)


@pytest.mark.django_db
class TestNotificationService:
    def test_send_welcome_email_no_template(self):
        from apps.payments_api.services import NotificationService
        user = UserFactory()
        NotificationService.send_welcome_email(user, user.tenant)
        from apps.notifications_api.models import Notification
        assert Notification.objects.count() == 0

    def test_send_welcome_email_with_template(self):
        from apps.payments_api.services import NotificationService
        from apps.notifications_api.models import NotificationTemplate, Notification
        tmpl = NotificationTemplate.objects.create(
            name='test_welcome',
            type='email',
            notification_type='welcome',
            subject='Bienvenido {{user_name}}',
            body='Hola {{user_name}}, bienvenido!',
            is_active=True
        )
        user = UserFactory()
        NotificationService.send_welcome_email(user, user.tenant)
        assert Notification.objects.filter(recipient=user).count() == 1

    def test_send_payment_confirmation(self):
        from apps.payments_api.services import NotificationService
        from apps.notifications_api.models import NotificationTemplate, Notification
        from apps.payments_api.models import Payment, PaymentProvider
        tmpl = NotificationTemplate.objects.create(
            name='test_payment', type='email',
            notification_type='payment_received',
            subject='Pago recibido', body='Gracias por tu pago', is_active=True
        )
        provider, _ = PaymentProvider.objects.get_or_create(name='stripe', defaults={'is_active': True})
        user = UserFactory()
        payment = Payment.objects.create(user=user, provider=provider, amount=Decimal('29.99'))
        NotificationService.send_payment_confirmation(user, payment)
        assert Notification.objects.filter(recipient=user).count() == 1
