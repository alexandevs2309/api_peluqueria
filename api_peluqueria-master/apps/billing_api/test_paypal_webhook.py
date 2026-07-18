"""
Tests de webhooks PayPal: PAYMENT.CAPTURE.COMPLETED, DENIED, REFUNDED.
"""
import json
import uuid
from decimal import Decimal
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auth_api.models import User
from apps.billing_api.models import Invoice, PaymentAttempt
from apps.billing_api.reconciliation_models import ProcessedPayPalEvent
from apps.payments_api.models import Payment, PaymentProvider
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────


def _make_tenant(suffix: str) -> tuple[User, Tenant]:
    plan, _ = SubscriptionPlan.objects.get_or_create(
        name="basic", defaults={"price": Decimal("10"), "duration_month": 1},
    )
    tenant = Tenant.objects.create(
        name=f"T-{suffix}", subdomain=f"t-{suffix}",
        subscription_plan=plan, subscription_status="trial", is_active=True,
    )
    user = User.objects.create_user(
        email=f"u-{suffix}@t.com", password="x", full_name="User", tenant=tenant,
    )
    return user, tenant


def _make_webhook_payload(event_type, resource, event_id=None):
    return {
        "id": event_id or str(uuid.uuid4()),
        "event_type": event_type,
        "resource": resource,
    }


def _make_capture_resource(user_id=1, capture_id="CAP-TEST-001", amount="10.00",
                           order_id="ORDER-TEST-001", status="COMPLETED"):
    return {
        "id": capture_id,
        "status": status,
        "amount": {"value": amount, "currency_code": "USD"},
        "purchase_units": [{
            "custom_id": f"user:{user_id}|tenant:1|plan:1|months:1",
        }],
        "supplementary_data": {
            "related_ids": {"order_id": order_id},
        },
    }


# ─────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_tenant():
    return _make_tenant("wh")


@pytest.fixture
def paypal_provider():
    provider, _ = PaymentProvider.objects.get_or_create(
        name='paypal', defaults={'is_active': True},
    )
    return provider


# ─────────────────────────────────────────
# Tests
# ─────────────────────────────────────────


class TestWebhookVerification:

    WEBHOOK_URL = reverse('paypal_webhook')

    @patch('apps.billing_api.paypal_webhook._verify_paypal_webhook', return_value=True)
    def test_unhandled_event_type_returns_200(self, mock_verify, api_client):
        """Eventos no manejados deben responder 200 OK."""
        payload = _make_webhook_payload("PAYMENT.SALE.COMPLETED", {})
        resp = api_client.post(self.WEBHOOK_URL, payload, format='json')
        assert resp.status_code == 200

    @patch('apps.billing_api.paypal_webhook._verify_paypal_webhook', return_value=False)
    def test_invalid_signature_returns_400(self, mock_verify, api_client):
        """Firma inválida debe rechazar con 400."""
        payload = _make_webhook_payload("PAYMENT.CAPTURE.COMPLETED", {})
        resp = api_client.post(self.WEBHOOK_URL, payload, format='json')
        assert resp.status_code == 400

    @patch('apps.billing_api.paypal_webhook._verify_paypal_webhook', return_value=True)
    def test_duplicate_event_id_skips_processing(self, mock_verify, api_client, user_tenant):
        """Mismo event_id no debe procesarse dos veces."""
        user, tenant = user_tenant
        event_id = "dupe-event-001"
        resource = _make_capture_resource(user.id)
        payload = _make_webhook_payload("PAYMENT.CAPTURE.COMPLETED", resource, event_id)

        resp1 = api_client.post(self.WEBHOOK_URL, payload, format='json')
        assert resp1.status_code == 200

        resp2 = api_client.post(self.WEBHOOK_URL, payload, format='json')
        assert resp2.status_code == 200

        assert Invoice.objects.count() == 1
        assert ProcessedPayPalEvent.objects.count() == 1


class TestCaptureCompleted:

    WEBHOOK_URL = reverse('paypal_webhook')

    @patch('apps.billing_api.paypal_webhook._verify_paypal_webhook', return_value=True)
    def test_creates_invoice_and_payment(self, mock_verify, api_client, user_tenant, paypal_provider):
        """PAYMENT.CAPTURE.COMPLETED debe crear Invoice + Payment."""
        user, tenant = user_tenant
        resource = _make_capture_resource(user.id)
        payload = _make_webhook_payload("PAYMENT.CAPTURE.COMPLETED", resource)

        resp = api_client.post(self.WEBHOOK_URL, payload, format='json')
        assert resp.status_code == 200

        invoice = Invoice.objects.filter(user=user).first()
        assert invoice is not None
        assert invoice.is_paid
        assert invoice.payment_method == 'paypal'
        assert invoice.paypal_order_id == 'ORDER-TEST-001'

        payment = Payment.objects.filter(user=user).first()
        assert payment is not None
        assert payment.status == 'completed'
        assert payment.provider_payment_id == 'CAP-TEST-001'

        # Verificar link Invoice -> Payment
        assert invoice.payment == payment

        # Verificar tenant activado
        tenant.refresh_from_db()
        assert tenant.subscription_status == 'active'

    @patch('apps.billing_api.paypal_webhook._verify_paypal_webhook', return_value=True)
    def test_idempotent_same_capture(self, mock_verify, api_client, user_tenant, paypal_provider):
        """Misma captura no debe crear duplicados."""
        user, tenant = user_tenant
        resource = _make_capture_resource(user.id)
        payload1 = _make_webhook_payload("PAYMENT.CAPTURE.COMPLETED", resource, "evt-1")
        payload2 = _make_webhook_payload("PAYMENT.CAPTURE.COMPLETED", resource, "evt-2")

        api_client.post(self.WEBHOOK_URL, payload1, format='json')
        api_client.post(self.WEBHOOK_URL, payload2, format='json')

        assert Invoice.objects.count() == 1
        assert Payment.objects.count() == 1

    @patch('apps.billing_api.paypal_webhook._verify_paypal_webhook', return_value=True)
    def test_creates_invoice_when_no_existing(self, mock_verify, api_client, paypal_provider):
        """Webhook debe crear Invoice incluso sin Invoice previa."""
        user, tenant = _make_tenant("wh-new")
        resource = _make_capture_resource(user.id, capture_id="CAP-NEW-001")
        payload = _make_webhook_payload("PAYMENT.CAPTURE.COMPLETED", resource)

        resp = api_client.post(self.WEBHOOK_URL, payload, format='json')
        assert resp.status_code == 200
        assert Invoice.objects.filter(user=user).exists()

    @patch('apps.billing_api.paypal_webhook._verify_paypal_webhook', return_value=True)
    def test_activates_tenant(self, mock_verify, api_client, user_tenant, paypal_provider):
        """Webhook debe cambiar tenant de past_due a active."""
        user, tenant = user_tenant
        tenant.subscription_status = 'past_due'
        tenant.save(update_fields=['subscription_status'])

        resource = _make_capture_resource(user.id)
        payload = _make_webhook_payload("PAYMENT.CAPTURE.COMPLETED", resource)

        api_client.post(self.WEBHOOK_URL, payload, format='json')

        tenant.refresh_from_db()
        assert tenant.subscription_status == 'active'

    @patch('apps.billing_api.paypal_webhook._verify_paypal_webhook', return_value=True)
    def test_skips_when_user_not_found(self, mock_verify, api_client):
        """Usuario inexistente no debe crear Invoice."""
        resource = _make_capture_resource(user_id=99999)
        payload = _make_webhook_payload("PAYMENT.CAPTURE.COMPLETED", resource)

        api_client.post(self.WEBHOOK_URL, payload, format='json')
        assert Invoice.objects.count() == 0

    @patch('apps.billing_api.paypal_webhook._verify_paypal_webhook', return_value=True)
    def test_skips_for_inactive_tenant(self, mock_verify, api_client, user_tenant):
        """Tenant is_active=False no debe procesarse."""
        user, tenant = user_tenant
        tenant.is_active = False
        tenant.save(update_fields=['is_active'])

        resource = _make_capture_resource(user.id)
        payload = _make_webhook_payload("PAYMENT.CAPTURE.COMPLETED", resource)

        api_client.post(self.WEBHOOK_URL, payload, format='json')
        assert Invoice.objects.count() == 0


class TestCaptureDenied:

    WEBHOOK_URL = reverse('paypal_webhook')

    @patch('apps.billing_api.paypal_webhook._verify_paypal_webhook', return_value=True)
    def test_creates_failed_invoice_and_attempt(self, mock_verify, api_client, user_tenant):
        """PAYMENT.CAPTURE.DENIED debe crear Invoice fallido + PaymentAttempt."""
        user, tenant = user_tenant
        resource = {
            "id": "CAP-DENIED-001",
            "status": "DENIED",
            "failure_reason": "DECLINED",
            "purchase_units": [{"custom_id": f"user:{user.id}|tenant:{tenant.id}"}],
        }
        payload = _make_webhook_payload("PAYMENT.CAPTURE.DENIED", resource)

        resp = api_client.post(self.WEBHOOK_URL, payload, format='json')
        assert resp.status_code == 200

        attempt = PaymentAttempt.objects.filter(invoice__user=user).first()
        assert attempt is not None
        assert not attempt.success
        assert "CAP-DENIED-001" in attempt.message

    @patch('apps.billing_api.paypal_webhook._verify_paypal_webhook', return_value=True)
    def test_idempotent_same_capture_denied(self, mock_verify, api_client, user_tenant):
        """Misma captura denegada con distinto event_id no debe crear duplicados."""
        user, tenant = user_tenant
        resource = {
            "id": "CAP-DENIED-IDEM-001",
            "status": "DENIED",
            "failure_reason": "DECLINED",
            "purchase_units": [{"custom_id": f"user:{user.id}|tenant:{tenant.id}"}],
        }
        payload1 = _make_webhook_payload("PAYMENT.CAPTURE.DENIED", resource, "evt-denied-1")
        payload2 = _make_webhook_payload("PAYMENT.CAPTURE.DENIED", resource, "evt-denied-2")

        api_client.post(self.WEBHOOK_URL, payload1, format='json')
        api_client.post(self.WEBHOOK_URL, payload2, format='json')

        attempts = PaymentAttempt.objects.filter(invoice__user=user)
        assert attempts.count() == 1

    @patch('apps.billing_api.paypal_webhook._verify_paypal_webhook', return_value=True)
    def test_suspends_after_3_denials(self, mock_verify, api_client, user_tenant):
        """3 denegaciones deben suspender el tenant."""
        user, tenant = user_tenant

        for i in range(3):
            resource = {
                "id": f"CAP-DENIED-{i}",
                "status": "DENIED",
                "failure_reason": "DECLINED",
                "purchase_units": [{"custom_id": f"user:{user.id}|tenant:{tenant.id}"}],
            }
            payload = _make_webhook_payload(
                "PAYMENT.CAPTURE.DENIED", resource, f"evt-denied-suspend-{i}"
            )
            api_client.post(self.WEBHOOK_URL, payload, format='json')

        tenant.refresh_from_db()
        assert tenant.subscription_status == 'suspended'
        assert not tenant.is_active


class TestCaptureRefunded:

    WEBHOOK_URL = reverse('paypal_webhook')

    @patch('apps.billing_api.paypal_webhook._verify_paypal_webhook', return_value=True)
    def test_marks_invoice_refunded(self, mock_verify, api_client, user_tenant, paypal_provider):
        """PAYMENT.CAPTURE.REFUNDED debe marcar Invoice como refunded."""
        user, tenant = user_tenant
        # Crear Invoice pagada primero
        payment = Payment.objects.create(
            user=user, tenant=tenant,
            provider=paypal_provider,
            amount=Decimal("10.00"), currency='USD',
            status='completed',
            provider_payment_id='CAP-REFUND-001',
        )
        invoice = Invoice.objects.create(
            user=user, tenant=tenant,
            amount=Decimal("10.00"),
            due_date=timezone.now(),
            is_paid=True, paid_at=timezone.now(),
            payment_method='paypal', status='paid',
            stripe_payment_intent_id='CAP-REFUND-001',
            paypal_order_id='ORDER-REFUND-001',
            payment=payment,
        )

        resource = {
            "id": "CAP-REFUND-001",
            "amount": {"value": "10.00", "currency_code": "USD"},
            "purchase_units": [{"custom_id": f"user:{user.id}|tenant:{tenant.id}"}],
        }
        payload = _make_webhook_payload("PAYMENT.CAPTURE.REFUNDED", resource)

        api_client.post(self.WEBHOOK_URL, payload, format='json')

        invoice.refresh_from_db()
        assert invoice.status == 'refunded'
        assert not invoice.is_paid

        payment.refresh_from_db()
        assert payment.status == 'refunded'

    @patch('apps.billing_api.paypal_webhook._verify_paypal_webhook', return_value=True)
    def test_no_invoice_no_crash(self, mock_verify, api_client, user_tenant):
        """Refund sin Invoice existente no debe crash."""
        user, tenant = user_tenant
        resource = {
            "id": "CAP-NO-INVOICE",
            "amount": {"value": "10.00", "currency_code": "USD"},
            "purchase_units": [{"custom_id": f"user:{user.id}|tenant:{tenant.id}"}],
        }
        payload = _make_webhook_payload("PAYMENT.CAPTURE.REFUNDED", resource)

        resp = api_client.post(self.WEBHOOK_URL, payload, format='json')
        assert resp.status_code == 200
