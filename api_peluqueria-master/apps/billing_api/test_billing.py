import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from django.urls import reverse
from apps.auth_api.factories import UserFactory
from apps.billing_api.models import Invoice, PaymentAttempt
from apps.subscriptions_api.models import UserSubscription, SubscriptionPlan


@pytest.fixture
def subscription_plan():
    return SubscriptionPlan.objects.create(
        name='basic',
        price=Decimal('29.99'),
        is_active=True
    )


@pytest.fixture
def user_with_subscription(subscription_plan):
    user = UserFactory()
    sub = UserSubscription.objects.create(
        user=user,
        plan=subscription_plan,
        is_active=True
    )
    return user, sub


@pytest.fixture
def invoice(user_with_subscription):
    user, sub = user_with_subscription
    return Invoice.objects.create(
        user=user,
        subscription=sub,
        amount=Decimal('29.99'),
        due_date=timezone.now() + timedelta(days=30),
        status='pending'
    )


@pytest.mark.django_db
class TestInvoiceModel:
    def test_create_invoice(self, user_with_subscription):
        user, sub = user_with_subscription
        invoice = Invoice.objects.create(
            user=user,
            subscription=sub,
            amount=Decimal('50.00'),
            due_date=timezone.now() + timedelta(days=15),
            status='pending'
        )
        assert invoice.id is not None
        assert invoice.is_paid is False
        assert str(invoice) == f"Invoice #{invoice.id} - {user.email}"

    def test_invoice_immutable_amount(self, invoice):
        with pytest.raises(Exception):
            invoice.amount = Decimal('99.99')
            invoice.save()

    def test_invoice_immutable_user(self, invoice):
        other_user = UserFactory()
        with pytest.raises(Exception):
            invoice.user = other_user
            invoice.save()

    def test_invoice_str(self, invoice):
        assert invoice.user.email in str(invoice)
        assert '#' in str(invoice)


@pytest.mark.django_db
class TestPaymentAttemptModel:
    def test_create_payment_attempt(self, invoice):
        attempt = PaymentAttempt.objects.create(
            invoice=invoice,
            success=True,
            status='success'
        )
        assert attempt.id is not None
        assert attempt.success is True
        assert str(attempt) == f"Attempt for Invoice #{invoice.id} - success"

    def test_failed_payment_attempt(self, invoice):
        attempt = PaymentAttempt.objects.create(
            invoice=invoice,
            success=False,
            status='failed',
            message='Tarjeta declinada'
        )
        assert attempt.success is False
        assert attempt.status == 'failed'


@pytest.mark.django_db
class TestInvoiceAPI:
    def test_list_invoices_requires_auth(self, api_client):
        url = reverse('invoice-list')
        response = api_client.get(url)
        assert response.status_code in [401, 403]

    def test_create_invoice(self, authorized_user, subscription_plan):
        user, client = authorized_user
        sub = UserSubscription.objects.create(user=user, plan=subscription_plan, is_active=True)
        url = reverse('invoice-list')
        data = {
            'subscription': sub.id,
            'due_date': (timezone.now() + timedelta(days=30)).isoformat(),
        }
        response = client.post(url, data)
        assert response.status_code == 201

    def test_update_invoice_returns_405(self, authorized_user, subscription_plan):
        user, client = authorized_user
        sub = UserSubscription.objects.create(user=user, plan=subscription_plan, is_active=True)
        invoice = Invoice.objects.create(user=user, subscription=sub, amount=Decimal('29.99'), due_date=timezone.now() + timedelta(days=30))
        url = reverse('invoice-detail', args=[invoice.id])
        response = client.patch(url, {'status': 'paid'})
        assert response.status_code == 405

    def test_delete_invoice_returns_405(self, authorized_user, subscription_plan):
        user, client = authorized_user
        sub = UserSubscription.objects.create(user=user, plan=subscription_plan, is_active=True)
        invoice = Invoice.objects.create(user=user, subscription=sub, amount=Decimal('29.99'), due_date=timezone.now() + timedelta(days=30))
        url = reverse('invoice-detail', args=[invoice.id])
        response = client.delete(url)
        assert response.status_code == 405

    def test_mark_as_paid_returns_403(self, authorized_user, subscription_plan):
        user, client = authorized_user
        sub = UserSubscription.objects.create(user=user, plan=subscription_plan, is_active=True)
        invoice = Invoice.objects.create(user=user, subscription=sub, amount=Decimal('29.99'), due_date=timezone.now() + timedelta(days=30), tenant=user.tenant)
        url = reverse('invoice-mark-as-paid', args=[invoice.id])
        response = client.post(url)
        assert response.status_code == 403

    def test_pay_returns_403(self, authorized_user, subscription_plan):
        user, client = authorized_user
        sub = UserSubscription.objects.create(user=user, plan=subscription_plan, is_active=True)
        invoice = Invoice.objects.create(user=user, subscription=sub, amount=Decimal('29.99'), due_date=timezone.now() + timedelta(days=30), tenant=user.tenant)
        url = reverse('invoice-pay', args=[invoice.id])
        response = client.post(url)
        assert response.status_code == 403

    def test_retrieve_invoice(self, authorized_user, subscription_plan):
        user, client = authorized_user
        sub = UserSubscription.objects.create(user=user, plan=subscription_plan, is_active=True)
        invoice = Invoice.objects.create(user=user, subscription=sub, amount=Decimal('29.99'), due_date=timezone.now() + timedelta(days=30), tenant=user.tenant)
        url = reverse('invoice-detail', args=[invoice.id])
        response = client.get(url)
        assert response.status_code == 200
        assert 'amount' in response.data


@pytest.mark.django_db
class TestPaymentAttemptAPI:
    def test_create_payment_attempt(self, authorized_user, subscription_plan):
        user, client = authorized_user
        sub = UserSubscription.objects.create(user=user, plan=subscription_plan, is_active=True)
        invoice = Invoice.objects.create(user=user, subscription=sub, amount=Decimal('29.99'), due_date=timezone.now() + timedelta(days=30))
        url = reverse('payment-attempt-list')
        data = {'invoice': invoice.id, 'success': True, 'status': 'success'}
        response = client.post(url, data)
        assert response.status_code == 201

    def test_list_payment_attempts_requires_auth(self, api_client):
        url = reverse('payment-attempt-list')
        response = api_client.get(url)
        assert response.status_code in [401, 403]


@pytest.mark.django_db
class TestBillingTasks:
    def test_fetch_stripe_payments_empty(self):
        from apps.billing_api.tasks import fetch_stripe_payments
        from unittest.mock import patch
        with patch('apps.billing_api.tasks.stripe.PaymentIntent.list') as mock_list:
            mock_list.return_value.auto_paging_iter.return_value = []
            result = fetch_stripe_payments(timezone.now() - timedelta(hours=1), timezone.now())
            assert result == []

    def test_daily_reconciliation_creates_log(self):
        from apps.billing_api.tasks import daily_financial_reconciliation
        from unittest.mock import patch
        with patch('apps.billing_api.tasks.fetch_stripe_payments', return_value=[]):
            result = daily_financial_reconciliation()
            assert result['status'] == 'completed'


@pytest.mark.django_db
class TestInvoiceSerializers:
    def test_invoice_serializer_validate_amount_positive(self):
        from apps.billing_api.serializers import InvoiceSerializer
        serializer = InvoiceSerializer()
        from rest_framework import serializers
        with pytest.raises(serializers.ValidationError):
            serializer.validate_amount(-10)

    def test_invoice_serializer_validate_due_date_future(self):
        from apps.billing_api.serializers import InvoiceSerializer
        serializer = InvoiceSerializer(data={'amount': 50, 'due_date': (timezone.now() - timedelta(days=1)).isoformat()})
        assert not serializer.is_valid()
        assert 'due_date' in serializer.errors
