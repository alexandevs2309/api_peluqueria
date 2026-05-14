"""
Webhook idempotente para eventos PayPal.
Validacion de firma: PayPal Webhook ID + notification headers.
"""
import json
import hashlib
import base64
import logging
import requests
from datetime import datetime, timezone as dt_timezone

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.db import transaction

from apps.auth_api.models import User
from apps.tenants_api.utils import get_active_tenant
from apps.billing_api.models import Invoice, PaymentAttempt
from apps.billing_api.reconciliation_models import ProcessedPayPalEvent

logger = logging.getLogger(__name__)


def _verify_paypal_webhook(request_body, headers_dict):
    """
    Verificar firma del webhook PayPal usando verify-webhook-signature API.
    """
    webhook_id = getattr(settings, 'PAYPAL_WEBHOOK_ID', '')
    if not webhook_id:
        logger.error("PAYPAL_WEBHOOK_ID not configured")
        return False

    auth_algo = headers_dict.get('HTTP_PAYPAL_AUTH_ALGO', '')
    cert_url = headers_dict.get('HTTP_PAYPAL_CERT_URL', '')
    transmission_id = headers_dict.get('HTTP_PAYPAL_TRANSMISSION_ID', '')
    transmission_sig = headers_dict.get('HTTP_PAYPAL_TRANSMISSION_SIG', '')
    transmission_time = headers_dict.get('HTTP_PAYPAL_TRANSMISSION_TIME', '')

    if not all([auth_algo, cert_url, transmission_id, transmission_sig, transmission_time]):
        logger.warning("PayPal webhook missing required headers")
        return False

    sandbox = getattr(settings, 'PAYPAL_SANDBOX', True)
    base_url = 'https://api.sandbox.paypal.com' if sandbox else 'https://api.paypal.com'

    client_id = getattr(settings, 'PAYPAL_CLIENT_ID', '')
    client_secret = getattr(settings, 'PAYPAL_SECRET', '')

    try:
        auth_resp = requests.post(
            f"{base_url}/v1/oauth2/token",
            headers={'Accept': 'application/json'},
            data='grant_type=client_credentials',
            auth=(client_id, client_secret),
            timeout=15,
        )
        if auth_resp.status_code != 200:
            logger.warning("PayPal auth failed for webhook verification")
            return False

        token = auth_resp.json().get('access_token')

        verify_payload = {
            'auth_algo': auth_algo,
            'cert_url': cert_url,
            'transmission_id': transmission_id,
            'transmission_sig': transmission_sig,
            'transmission_time': transmission_time,
            'webhook_id': webhook_id,
            'webhook_event': json.loads(request_body) if isinstance(request_body, (bytes, str)) else request_body,
        }

        verify_resp = requests.post(
            f"{base_url}/v1/notifications/verify-webhook-signature",
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            json=verify_payload,
            timeout=15,
        )

        if verify_resp.status_code != 200:
            logger.warning("PayPal verify-webhook-signature failed status=%s", verify_resp.status_code)
            return False

        result = verify_resp.json()
        return result.get('verification_status') == 'SUCCESS'

    except requests.RequestException as exc:
        logger.exception("PayPal webhook verification request failed: %s", exc)
        return False


def _resolve_user_from_paypal_resource(resource):
    """Extraer user_id desde custom_id en purchase_units."""
    custom_id = (resource.get('purchase_units') or [{}])[0].get('custom_id', '')
    if not custom_id:
        logger.warning("PayPal webhook: missing custom_id in resource")
        return None

    for part in custom_id.split('|'):
        if part.startswith('user:'):
            try:
                return int(part.split(':', 1)[1])
            except (ValueError, IndexError):
                return None
    logger.warning("PayPal webhook: user_id not found in custom_id=%s", custom_id)
    return None


def _resolve_capture_details(resource):
    """Extraer amount y capture_id del evento PAYMENT.CAPTURE.COMPLETED."""
    amount = resource.get('amount', {})
    return {
        'capture_id': resource.get('id', ''),
        'amount': float(amount.get('value', 0)),
        'currency': amount.get('currency_code', 'USD'),
    }


def handle_capture_completed(resource):
    """Manejar PAYMENT.CAPTURE.COMPLETED — crear factura y activar tenant."""
    user_id = _resolve_user_from_paypal_resource(resource)
    if not user_id:
        logger.warning("Capture completed: missing user_id")
        return

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.warning("Capture completed: user %s not found", user_id)
        return

    if hasattr(user, 'tenant') and user.tenant:
        try:
            get_active_tenant(user.tenant.id)
        except Exception as exc:
            logger.warning("Capture completed for inactive tenant %s: %s", user.tenant.id, exc)
            return

    capture = _resolve_capture_details(resource)
    custom_id = (resource.get('purchase_units') or [{}])[0].get('custom_id', '')
    description = f"PayPal capture {capture['capture_id']}"

    with transaction.atomic():
        existing = Invoice.objects.filter(
            stripe_payment_intent_id=capture['capture_id'],
        ).select_for_update().first()

        if existing:
            if existing.is_paid:
                logger.info("Invoice for capture %s already paid", capture['capture_id'])
                return
            existing.is_paid = True
            existing.paid_at = datetime.now(tz=dt_timezone.utc)
            existing.payment_method = 'paypal'
            existing.status = 'paid'
            existing.save()
        else:
            Invoice.objects.create(
                user=user,
                amount=capture['amount'],
                due_date=datetime.now(tz=dt_timezone.utc),
                is_paid=True,
                paid_at=datetime.now(tz=dt_timezone.utc),
                payment_method='paypal',
                status='paid',
                stripe_payment_intent_id=capture['capture_id'],
                description=description,
            )

        if hasattr(user, 'tenant') and user.tenant:
            tenant = user.tenant
            update_fields = []
            if tenant.subscription_status != 'active':
                tenant.subscription_status = 'active'
                update_fields.append('subscription_status')
            if not tenant.is_active:
                tenant.is_active = True
                update_fields.append('is_active')
            if update_fields:
                update_fields.append('updated_at')
                tenant.save(update_fields=update_fields)


def handle_capture_denied(resource):
    """Manejar PAYMENT.CAPTURE.DENIED."""
    user_id = _resolve_user_from_paypal_resource(resource)
    if not user_id:
        return

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    failure_reason = resource.get('failure_reason', 'Unknown')
    invoice = Invoice.objects.filter(user=user, is_paid=False).order_by('-id').first()
    PaymentAttempt.objects.create(
        invoice=invoice,
        success=False,
        status='failed',
        message=f"PayPal capture denied: {failure_reason}",
    )

    if hasattr(user, 'tenant') and user.tenant:
        failed_attempts = PaymentAttempt.objects.filter(invoice__user=user, success=False).count()
        if failed_attempts >= 3:
            tenant = user.tenant
            tenant.subscription_status = 'suspended'
            tenant.is_active = False
            tenant.save(update_fields=['subscription_status', 'is_active', 'updated_at'])
            logger.warning("Tenant %s suspended after %d failed PayPal payments", tenant.id, failed_attempts)


def handle_capture_refunded(resource):
    """Manejar PAYMENT.CAPTURE.REFUNDED."""
    user_id = _resolve_user_from_paypal_resource(resource)
    if not user_id:
        return

    capture_id = resource.get('id', '')
    Invoice.objects.filter(stripe_payment_intent_id=capture_id).update(
        status='refunded',
        is_paid=False,
    )
    logger.info("Invoice for capture %s marked as refunded", capture_id)


EVENT_HANDLERS = {
    'PAYMENT.CAPTURE.COMPLETED': handle_capture_completed,
    'PAYMENT.CAPTURE.DENIED': handle_capture_denied,
    'PAYMENT.CAPTURE.REFUNDED': handle_capture_refunded,
}


@csrf_exempt
@require_POST
def paypal_webhook(request):
    """Webhook idempotente para eventos PayPal."""
    try:
        event = json.loads(request.body)
    except json.JSONDecodeError:
        logger.warning("PayPal webhook: invalid JSON")
        return HttpResponse(status=400)

    event_id = event.get('id', '')
    event_type = event.get('event_type', '')

    if not event_id or not event_type:
        logger.warning("PayPal webhook: missing event_id or event_type")
        return HttpResponse(status=400)

    if not _verify_paypal_webhook(request.body, request.META):
        logger.warning("PayPal webhook: signature verification failed event_id=%s", event_id)
        return HttpResponse(status=400)

    try:
        with transaction.atomic():
            event_obj, created = ProcessedPayPalEvent.objects.get_or_create(
                paypal_event_id=event_id,
                defaults={
                    'event_type': event_type,
                    'payload': event.get('resource', {}),
                }
            )

            if not created:
                logger.info("PayPal event %s already processed", event_id)
                return HttpResponse(status=200)

            handler = EVENT_HANDLERS.get(event_type)
            if handler:
                handler(event.get('resource', {}))
            else:
                logger.info("PayPal unhandled event type: %s", event_type)

        logger.info("PayPal event %s (%s) processed", event_id, event_type)
        return HttpResponse(status=200)

    except Exception as exc:
        logger.exception("PayPal webhook error event_id=%s: %s", event_id, exc)
        return HttpResponse(status=500)
