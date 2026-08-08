"""
Tests de flujo PayPal: create order, capture, webhook, race conditions, edge cases.
"""
import json
import uuid
from decimal import Decimal
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.auth_api.models import User
from apps.billing_api.models import Invoice, PaymentAttempt
from apps.billing_api.reconciliation_models import ProcessedPayPalEvent
from apps.payments_api.models import PaymentProvider
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan
from apps.subscriptions_api import views as subscription_views


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────


def _make_tenant(suffix: str) -> tuple[User, Tenant]:
    plan, _ = SubscriptionPlan.objects.get_or_create(
        name="basic", defaults={"price": Decimal("10"), "duration_month": 1},
    )
    tenant = Tenant.objects.create(
        name=f"T-{suffix}", subdomain=f"t-{suffix}",
        subscription_plan=plan, subscription_status="active", is_active=True,
    )
    user = User.objects.create_user(
        email=f"u-{suffix}@t.com", password="x", full_name="User", tenant=tenant,
    )
    return user, tenant


def _stub_paypal_auth():
    return "fake-token", None


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear Django cache before each test to avoid cross-test pollution."""
    cache.clear()


# ─────────────────────────────────────────
# Create Order
# ─────────────────────────────────────────


@pytest.mark.django_db
def test_paypal_create_order_success(monkeypatch):
    user, tenant = _make_tenant("create-ok")
    plan = tenant.subscription_plan

    monkeypatch.setattr("apps.payments_api.services.PayPalService.get_access_token", lambda s: _stub_paypal_auth())
    monkeypatch.setattr("apps.payments_api.services.PayPalService.create_order", lambda s, *a, **kw: ({
        "order_id": "ORDER-CREATE-OK",
        "approve_url": "https://paypal.test/approve/ORDER-CREATE-OK",
        "sandbox": True,
        "amount": "10.00",
    }, None))

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(reverse("renew-subscription"), {
        "payment_provider": "paypal",
        "paypal_action": "create_order",
        "plan_id": plan.id,
        "months": 1,
        "auto_renew": False,
    }, format="json")

    assert resp.status_code == 200
    assert resp.data["provider"] == "paypal"
    assert resp.data["order_id"] == "ORDER-CREATE-OK"
    assert "paypal.test" in resp.data["approve_url"]


@pytest.mark.django_db
def test_paypal_create_order_rejects_auto_renew(monkeypatch):
    user, tenant = _make_tenant("create-no-auto")
    plan = tenant.subscription_plan

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(reverse("renew-subscription"), {
        "payment_provider": "paypal",
        "paypal_action": "create_order",
        "plan_id": plan.id,
        "months": 1,
        "auto_renew": True,
    }, format="json")

    assert resp.status_code == 400
    assert "auto-renew" in str(resp.data).lower()


# ─────────────────────────────────────────
# Capture Order
# ─────────────────────────────────────────


@pytest.mark.django_db
def test_paypal_capture_order_success(monkeypatch, paypal_provider):
    user, tenant = _make_tenant("capture-ok")
    plan = tenant.subscription_plan

    monkeypatch.setattr("apps.payments_api.services.PayPalService.get_access_token", lambda s: _stub_paypal_auth())
    monkeypatch.setattr("apps.payments_api.services.PayPalService.create_order", lambda s, *a, **kw: ({
        "order_id": "ORDER-CAPTURE-OK",
        "approve_url": "https://paypal.test/approve/ORDER-CAPTURE-OK",
        "sandbox": True,
        "amount": "10.00",
    }, None))
    monkeypatch.setattr("apps.payments_api.services.PayPalService.capture_order", lambda s, *a, **kw: ({
        "capture_id": "CAP-CAPTURE-OK",
        "status": "COMPLETED",
        "amount": 10.00,
        "currency": "USD",
    }, None))

    client = APIClient()
    client.force_authenticate(user=user)

    # Create
    create_resp = client.post(reverse("renew-subscription"), {
        "payment_provider": "paypal",
        "paypal_action": "create_order",
        "plan_id": plan.id,
        "months": 1,
        "auto_renew": False,
    }, format="json")
    assert create_resp.status_code == 200
    order_id = create_resp.data["order_id"]

    # Capture
    resp = client.post(reverse("renew-subscription"), {
        "payment_provider": "paypal",
        "paypal_action": "capture_order",
        "paypal_order_id": order_id,
    }, format="json")

    assert resp.status_code == 200
    assert resp.data["provider"] == "paypal"
    assert resp.data["status"] == "active"

    # Verificar Invoice creada con tenant
    invoice = Invoice.objects.filter(user=user).first()
    assert invoice is not None
    assert invoice.tenant == tenant, "Invoice MUST have tenant"
    assert invoice.is_paid
    assert invoice.payment_method == "paypal"
    assert invoice.stripe_payment_intent_id, "Invoice should store PayPal capture_id"

    # Verificar Payment unificado
    assert invoice.payment is not None
    assert invoice.payment.status == 'completed'


@pytest.mark.django_db
def test_paypal_capture_order_expired_cache(monkeypatch):
    """Si el caché expiró entre create y capture, debe dar 410 Gone."""
    user, tenant = _make_tenant("capture-expired")
    plan = tenant.subscription_plan

    monkeypatch.setattr("apps.payments_api.services.PayPalService.get_access_token", lambda s: _stub_paypal_auth())

    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.post(reverse("renew-subscription"), {
        "payment_provider": "paypal",
        "paypal_action": "capture_order",
        "paypal_order_id": "ORDER-NONEXISTENT",
    }, format="json")

    assert resp.status_code == 410
    assert "expir" in str(resp.data).lower()


@pytest.mark.django_db
def test_paypal_capture_order_mismatch(monkeypatch):
    """Usuario B no puede capturar orden creada por usuario A."""
    user_a, tenant_a = _make_tenant("mismatch-a")
    user_b, tenant_b = _make_tenant("mismatch-b")
    plan = tenant_a.subscription_plan

    monkeypatch.setattr("apps.payments_api.services.PayPalService.get_access_token", lambda s: _stub_paypal_auth())
    monkeypatch.setattr("apps.payments_api.services.PayPalService.create_order", lambda s, *a, **kw: ({
        "order_id": "ORDER-MISMATCH",
        "approve_url": "https://paypal.test/approve/ORDER-MISMATCH",
        "sandbox": True,
        "amount": "10.00",
    }, None))

    client_a = APIClient()
    client_a.force_authenticate(user=user_a)
    create_resp = client_a.post(reverse("renew-subscription"), {
        "payment_provider": "paypal",
        "paypal_action": "create_order",
        "plan_id": plan.id,
        "months": 1,
        "auto_renew": False,
    }, format="json")
    assert create_resp.status_code == 200
    order_id = create_resp.data["order_id"]

    # User B intenta capturar la orden de User A
    client_b = APIClient()
    client_b.force_authenticate(user=user_b)
    resp = client_b.post(reverse("renew-subscription"), {
        "payment_provider": "paypal",
        "paypal_action": "capture_order",
        "paypal_order_id": order_id,
    }, format="json")

    assert resp.status_code == 403
    assert "mismatch" in str(resp.data).lower()


# ─────────────────────────────────────────
# Webhook — Capture Completed
# ─────────────────────────────────────────


@pytest.mark.django_db
def test_webhook_capture_completed_creates_invoice_with_tenant(monkeypatch):
    """BUGFIX: Invoice created by webhook MUST have tenant."""
    user, tenant = _make_tenant("wh-tenant-fix")
    custom_id = f"user:{user.id}|tenant:{tenant.id}|plan:{tenant.subscription_plan.id}|months:1"

    monkeypatch.setattr("apps.billing_api.paypal_webhook._verify_paypal_webhook", lambda b, h: True)

    client = APIClient()
    event_payload = {
        "id": f"EVENT-{uuid.uuid4().hex[:8]}",
        "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {
            "id": f"CAP-WH-{uuid.uuid4().hex[:4]}",
            "status": "COMPLETED",
            "amount": {"value": "10.00", "currency_code": "USD"},
            "purchase_units": [{"custom_id": custom_id}],
        },
    }

    resp = client.post("/api/billing/webhooks/paypal/", event_payload, format="json")
    assert resp.status_code == 200

    invoice = Invoice.objects.filter(user=user).first()
    assert invoice is not None
    assert invoice.tenant == tenant, f"BUG: Invoice tenant is None, expected {tenant.id}"
    assert invoice.is_paid
    assert invoice.payment_method == "paypal"


@pytest.mark.django_db
def test_webhook_idempotency(monkeypatch):
    """Mismo event_id no debe procesarse dos veces."""
    user, tenant = _make_tenant("wh-idemp")
    custom_id = f"user:{user.id}|tenant:{tenant.id}|plan:{tenant.subscription_plan.id}|months:1"

    monkeypatch.setattr("apps.billing_api.paypal_webhook._verify_paypal_webhook", lambda b, h: True)

    client = APIClient()
    event_id = f"EVENT-DUP-{uuid.uuid4().hex[:6]}"
    event_payload = {
        "id": event_id,
        "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {
            "id": "CAP-DUP",
            "status": "COMPLETED",
            "amount": {"value": "10.00", "currency_code": "USD"},
            "purchase_units": [{"custom_id": custom_id}],
        },
    }

    resp1 = client.post("/api/billing/webhooks/paypal/", event_payload, format="json")
    assert resp1.status_code == 200

    resp2 = client.post("/api/billing/webhooks/paypal/", event_payload, format="json")
    assert resp2.status_code == 200

    # Debe haber solo UNA Invoice
    assert Invoice.objects.filter(user=user).count() == 1
    assert ProcessedPayPalEvent.objects.filter(paypal_event_id=event_id).count() == 1


@pytest.mark.django_db
def test_webhook_capture_refunded_marks_invoice(monkeypatch):
    user, tenant = _make_tenant("wh-refund")
    Invoice.objects.create(
        user=user, tenant=tenant, amount=Decimal("10"),
        due_date=timezone.now(),
        is_paid=True, paid_at=timezone.now(), payment_method="paypal",
        status="paid", stripe_payment_intent_id="CAP-REFUND-001",
    )

    monkeypatch.setattr("apps.billing_api.paypal_webhook._verify_paypal_webhook", lambda b, h: True)

    client = APIClient()
    resp = client.post("/api/billing/webhooks/paypal/", {
        "id": f"EVENT-REFUND-{uuid.uuid4().hex[:6]}",
        "event_type": "PAYMENT.CAPTURE.REFUNDED",
        "resource": {"id": "CAP-REFUND-001", "purchase_units": [{"custom_id": f"user:{user.id}"}]},
    }, format="json")
    assert resp.status_code == 200

    invoice = Invoice.objects.get(stripe_payment_intent_id="CAP-REFUND-001")
    assert invoice.status == "refunded"
    assert not invoice.is_paid


@pytest.mark.django_db
def test_webhook_capture_denied_creates_payment_attempt(monkeypatch):
    user, tenant = _make_tenant("wh-denied")
    custom_id = f"user:{user.id}|tenant:{tenant.id}|plan:{tenant.subscription_plan.id}|months:1"

    monkeypatch.setattr("apps.billing_api.paypal_webhook._verify_paypal_webhook", lambda b, h: True)

    client = APIClient()
    resp = client.post("/api/billing/webhooks/paypal/", {
        "id": f"EVENT-DENIED-{uuid.uuid4().hex[:6]}",
        "event_type": "PAYMENT.CAPTURE.DENIED",
        "resource": {
            "id": "CAP-DENIED-001",
            "status": "DENIED",
            "failure_reason": "INSTRUMENT_DECLINED",
            "purchase_units": [{"custom_id": custom_id}],
        },
    }, format="json")
    assert resp.status_code == 200

    attempt = PaymentAttempt.objects.last()
    assert attempt is not None
    assert not attempt.success


# ─────────────────────────────────────────
# Race condition: capture + webhook duplicados
# ─────────────────────────────────────────


@pytest.mark.django_db
def test_capture_and_webhook_do_not_create_duplicate_invoices(monkeypatch, paypal_provider):
    """
    BUGFIX: Cuando _capture_paypal_order y handle_capture_completed
    se ejecutan para el mismo pago, NO deben crear 2 Invoices.
    """
    user, tenant = _make_tenant("race")
    plan = tenant.subscription_plan

    ORDER_ID = "ORDER-RACE"
    CAPTURE_ID = "CAP-RACE"

    monkeypatch.setattr("apps.payments_api.services.PayPalService.get_access_token", lambda s: _stub_paypal_auth())
    monkeypatch.setattr("apps.payments_api.services.PayPalService.create_order", lambda s, *a, **kw: ({
        "order_id": ORDER_ID,
        "approve_url": f"https://paypal.test/approve/{ORDER_ID}",
        "sandbox": True,
        "amount": "10.00",
    }, None))
    monkeypatch.setattr("apps.payments_api.services.PayPalService.capture_order", lambda s, *a, **kw: ({
        "capture_id": CAPTURE_ID,
        "status": "COMPLETED",
        "amount": 10.00,
        "currency": "USD",
    }, None))
    monkeypatch.setattr("apps.billing_api.paypal_webhook._verify_paypal_webhook", lambda b, h: True)

    client = APIClient()
    client.force_authenticate(user=user)

    # Create order
    create_resp = client.post(reverse("renew-subscription"), {
        "payment_provider": "paypal",
        "paypal_action": "create_order",
        "plan_id": plan.id,
        "months": 1,
        "auto_renew": False,
    }, format="json")
    assert create_resp.status_code == 200

    # Capture
    capture_resp = client.post(reverse("renew-subscription"), {
        "payment_provider": "paypal",
        "paypal_action": "capture_order",
        "paypal_order_id": ORDER_ID,
    }, format="json")
    assert capture_resp.status_code == 200

    # Webhook llega después con el mismo capture_id
    webhook_resp = client.post("/api/billing/webhooks/paypal/", {
        "id": f"EVENT-RACE-{uuid.uuid4().hex[:6]}",
        "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {
            "id": CAPTURE_ID,
            "status": "COMPLETED",
            "amount": {"value": "10.00", "currency_code": "USD"},
            "purchase_units": [{"custom_id": f"user:{user.id}|tenant:{tenant.id}|plan:{plan.id}|months:1"}],
            "supplementary_data": {"related_ids": {"order_id": ORDER_ID}},
        },
    }, format="json")
    assert webhook_resp.status_code == 200

    # Solo una Invoice
    invoices = Invoice.objects.filter(user=user)
    assert invoices.count() == 1, f"BUG: {invoices.count()} invoices created instead of 1"

    invoice = invoices.first()
    assert invoice.tenant == tenant
    assert invoice.is_paid


# ─────────────────────────────────────────
# Webhook signature verification
# ─────────────────────────────────────────


@pytest.mark.django_db
def test_webhook_rejects_invalid_signature(monkeypatch):
    monkeypatch.setattr("apps.billing_api.paypal_webhook._verify_paypal_webhook", lambda b, h: False)

    client = APIClient()
    resp = client.post("/api/billing/webhooks/paypal/", {
        "id": "EVENT-BAD-SIG",
        "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {},
    }, format="json")
    assert resp.status_code == 400


@pytest.mark.django_db
def test_webhook_requires_valid_json():
    client = APIClient()
    resp = client.post("/api/billing/webhooks/paypal/",
        "not-json",
        content_type="application/json",
    )
    assert resp.status_code == 400


@pytest.fixture
def paypal_provider():
    provider, _ = PaymentProvider.objects.get_or_create(
        name='paypal', defaults={'is_active': True},
    )
    return provider
