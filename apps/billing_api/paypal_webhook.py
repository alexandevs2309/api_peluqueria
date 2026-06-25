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
from django.db import models, transaction

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


def _resolve_paypal_order_id(resource):
    """Extraer el PayPal order ID del resource del evento de captura."""
    # El resource de PAYMENT.CAPTURE.COMPLETED tiene supplementary_data.related_ids.order_id
    supplementary = resource.get('supplementary_data', {})
    related_ids = supplementary.get('related_ids', {})
    order_id = related_ids.get('order_id', '')
    if order_id:
        return order_id
    # Fallback: extraer del link con rel 'up' o 'order'
    links = resource.get('links', [])
    for link in links:
        if link.get('rel') in ('up', 'order') and link.get('href'):
            # Extraer el order ID de la URL /v2/checkout/orders/{order_id}
            href = link['href']
            if '/orders/' in href:
                return href.rsplit('/', 1)[-1]
    return ''


def handle_capture_completed(resource):
    """Manejar PAYMENT.CAPTURE.COMPLETED — crear factura, Payment y activar tenant."""
    from apps.payments_api.services import PayPalService

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
    paypal_order_id = _resolve_paypal_order_id(resource)
    description = f"PayPal capture {capture['capture_id']}"
    custom_id = (resource.get('purchase_units') or [{}])[0].get('custom_id', '')

    with transaction.atomic():
        id_filter = models.Q(stripe_payment_intent_id=capture['capture_id'])
        if paypal_order_id:
            id_filter = id_filter | models.Q(paypal_order_id=paypal_order_id)
        existing = Invoice.objects.filter(id_filter).select_for_update().first()

        if existing:
            if existing.is_paid:
                logger.info("Invoice for capture %s already paid", capture['capture_id'])
                return
            existing.is_paid = True
            existing.paid_at = datetime.now(tz=dt_timezone.utc)
            existing.payment_method = 'paypal'
            existing.status = 'paid'
            existing.stripe_payment_intent_id = existing.stripe_payment_intent_id or capture['capture_id']
            existing.paypal_order_id = existing.paypal_order_id or paypal_order_id or None
            existing.save()
        else:
            payment = PayPalService.create_payment_record(
                user=user,
                tenant=getattr(user, 'tenant', None),
                amount=capture['amount'],
                capture_id=capture['capture_id'],
                order_id=paypal_order_id,
            )
            Invoice.objects.create(
                user=user,
                tenant=getattr(user, 'tenant', None),
                amount=capture['amount'],
                due_date=datetime.now(tz=dt_timezone.utc),
                is_paid=True,
                paid_at=datetime.now(tz=dt_timezone.utc),
                payment_method='paypal',
                status='paid',
                stripe_payment_intent_id=capture['capture_id'],
                paypal_order_id=paypal_order_id or None,
                payment=payment,
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

        try:
            from apps.subscriptions_api.views import send_purchase_confirmation
            from apps.subscriptions_api.models import SubscriptionPlan
            plan_id = None
            months = 1
            for part in custom_id.split('|'):
                if part.startswith('plan:'):
                    plan_id = part.split(':', 1)[1]
                elif part.startswith('months:'):
                    months = int(part.split(':', 1)[1])
            if plan_id and hasattr(user, 'tenant'):
                plan = SubscriptionPlan.objects.get(id=int(plan_id))
                send_purchase_confirmation(
                    user, user.tenant, plan,
                    capture['amount'],
                    months,
                    payment_method='paypal'
                )
        except Exception:
            logger.exception("Error sending payment confirmation from PayPal webhook")


def handle_capture_denied(resource):
    """Manejar PAYMENT.CAPTURE.DENIED — con idempotencia."""
    user_id = _resolve_user_from_paypal_resource(resource)
    if not user_id:
        return

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    failure_reason = resource.get('failure_reason', 'Unknown')
    capture_id = resource.get('id', '')

    invoice = Invoice.objects.filter(user=user, is_paid=False).order_by('-id').first()
    if not invoice:
        invoice = Invoice.objects.create(
            user=user,
            tenant=getattr(user, 'tenant', None),
            amount=0,
            due_date=datetime.now(tz=dt_timezone.utc),
            is_paid=False,
            payment_method='paypal',
            status='failed',
            description=f"PayPal capture denied: {failure_reason}",
        )

    # Idempotencia: evitar duplicados si PayPal retransmite el mismo denied
    # con distinto event_id (get_or_create imposible sin unique en PaymentAttempt).
    if capture_id and PaymentAttempt.objects.filter(
        invoice=invoice, message__contains=capture_id
    ).exists():
        logger.info(
            "Denied capture %s already processed for invoice %s — skipping",
            capture_id, invoice.id
        )
        return

    PaymentAttempt.objects.create(
        invoice=invoice,
        success=False,
        status='failed',
        message=f"PayPal capture denied: {failure_reason} (capture: {capture_id})",
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
    """Manejar PAYMENT.CAPTURE.REFUNDED — marcar factura, suspender tenant y notificar."""
    from apps.auth_api.tasks import send_email_async

    user_id = _resolve_user_from_paypal_resource(resource)
    if not user_id:
        return

    capture_id = resource.get('id', '')
    amount = resource.get('amount', {}).get('value', '0')
    currency = resource.get('amount', {}).get('currency_code', 'USD')

    # Buscar la factura por capture_id o paypal_order_id
    invoice = Invoice.objects.filter(
        models.Q(stripe_payment_intent_id=capture_id) |
        models.Q(paypal_order_id=capture_id)
    ).first()

    if invoice:
        invoice.status = 'refunded'
        invoice.is_paid = False
        invoice.save(update_fields=['status', 'is_paid'])
        # Sincronizar Payment unificado
        if invoice.payment_id:
            try:
                from apps.payments_api.models import Payment
                Payment.objects.filter(id=invoice.payment_id).update(status='refunded')
            except Exception:
                logger.exception("Failed to update Payment status for invoice %s", invoice.id)
        logger.info("Invoice %s for capture %s marked as refunded", invoice.id, capture_id)

        # Suspender el tenant asociado
        tenant = invoice.tenant
        if tenant and hasattr(tenant, 'suspend_subscription'):
            try:
                tenant.suspend_subscription(save=True)
                logger.warning(
                    "Tenant %s suspended due to PayPal refund/chargeback on invoice %s",
                    tenant.id, invoice.id
                )
            except Exception as exc:
                logger.exception(
                    "Failed to suspend tenant %s after refund: %s", tenant.id, exc
                )
        elif not tenant:
            # Fallback: resolver tenant desde el usuario de la factura
            user = invoice.user
            if user and hasattr(user, 'tenant') and user.tenant:
                try:
                    user.tenant.suspend_subscription(save=True)
                    logger.warning(
                        "Tenant %s suspended (via user fallback) due to PayPal refund on invoice %s",
                        user.tenant.id, invoice.id
                    )
                except Exception as exc:
                    logger.exception(
                        "Failed to suspend tenant %s after refund (fallback): %s",
                        user.tenant.id, exc
                    )

        # Enviar notificación de chargeback/refund
        try:
            user = invoice.user
            subject = f"Reembolso/Chargeback recibido - {amount} {currency}"
            text_body = (
                f"Hola {user.full_name or user.email},\n\n"
                f"Se ha procesado un reembolso o chargeback en tu cuenta de PayPal "
                f"por {amount} {currency} (Factura #{invoice.id}).\n\n"
                f"Como resultado, tu suscripción ha sido suspendida.\n"
                f"Por favor, contacta a soporte para regularizar tu situación.\n\n"
                f"El equipo de AuronSuite"
            )
            html_body = (
                f"<h2>Reembolso/Chargeback recibido</h2>"
                f"<p>Hola {user.full_name or user.email},</p>"
                f"<p>Se ha procesado un reembolso o chargeback en tu cuenta de PayPal "
                f"por <strong>{amount} {currency}</strong> (Factura #{invoice.id}).</p>"
                f"<p>Como resultado, tu suscripción ha sido <strong>suspendida</strong>.</p>"
                f"<p>Por favor, contacta a <a href='mailto:soporte@auronsuite.com'>soporte@auronsuite.com</a> "
                f"para regularizar tu situación.</p>"
                f"<p>El equipo de AuronSuite</p>"
            )
            send_email_async.delay(
                subject, text_body, '',
                [user.email],
                html_message=html_body,
            )
            logger.info("Refund notification email sent to %s for invoice %s", user.email, invoice.id)
        except Exception as exc:
            logger.exception("Failed to send refund notification email: %s", exc)
    else:
        logger.warning("No invoice found for capture %s — cannot suspend tenant", capture_id)


def handle_subscription_activated(resource):
    """Manejar BILLING.SUBSCRIPTION.ACTIVATED."""
    from apps.subscriptions_api.models import Subscription, SubscriptionPlan
    
    sub_id = resource.get('id')
    custom_id = resource.get('custom_id') or ''
    
    user_id, tenant_id, plan_id, interval = None, None, None, 'month'
    for part in custom_id.split('|'):
        if part.startswith('user:'): user_id = part.split(':')[1]
        elif part.startswith('tenant:'): tenant_id = part.split(':')[1]
        elif part.startswith('plan:'): plan_id = part.split(':')[1]
        elif part.startswith('interval:'): interval = part.split(':')[1]

    if not sub_id or not tenant_id or not plan_id:
        logger.warning("Subscription activated missing vital custom_id data: %s", custom_id)
        return

    try:
        plan = SubscriptionPlan.objects.get(id=plan_id)
        Subscription.objects.update_or_create(
            tenant_id=tenant_id,
            plan=plan,
            defaults={
                'paypal_subscription_id': sub_id,
                'is_active': True,
                'billing_interval': interval
            }
        )
        logger.info("Subscription %s activated for tenant %s", sub_id, tenant_id)
    except Exception as e:
        logger.exception("Error handling subscription activated: %s", e)


def handle_subscription_cancelled(resource):
    """Manejar BILLING.SUBSCRIPTION.CANCELLED."""
    from apps.subscriptions_api.models import Subscription
    sub_id = resource.get('id')
    if not sub_id: return
    
    Subscription.objects.filter(paypal_subscription_id=sub_id).update(is_active=False)
    logger.info("Subscription %s cancelled via webhook", sub_id)


def handle_payment_sale_completed(resource):
    """Manejar PAYMENT.SALE.COMPLETED."""
    from apps.subscriptions_api.models import Subscription
    from apps.payments_api.services import PayPalService
    from dateutil.relativedelta import relativedelta
    
    sub_id = resource.get('billing_agreement_id')
    amount_str = resource.get('amount', {}).get('total', '0')
    sale_id = resource.get('id')
    
    if not sub_id:
        logger.warning("Sale completed missing billing_agreement_id (subscription id)")
        return
        
    subscription = Subscription.objects.filter(paypal_subscription_id=sub_id).first()
    if not subscription:
        logger.warning("Sale completed for unknown subscription %s", sub_id)
        return
        
    tenant = subscription.tenant
    user = tenant.owner if hasattr(tenant, 'owner') else None  # fallback si no hay custom_id
    if not user:
        # Intenta obtener de custom_id si viene en el recurso, las sales no siempre lo traen
        custom = resource.get('custom', '')
        for part in custom.split('|'):
            if part.startswith('user:'):
                try: user = User.objects.get(id=part.split(':')[1])
                except: pass
                
    months = 12 if subscription.billing_interval == 'year' else 1
    
    with transaction.atomic():
        now = datetime.now(tz=dt_timezone.utc)
        base_time = now
        if tenant.access_until and tenant.access_until > now:
            base_time = tenant.access_until
        access_until = base_time + relativedelta(months=months)
        
        tenant.access_until = access_until
        tenant.subscription_status = 'active'
        tenant.is_active = True
        tenant.save(update_fields=['access_until', 'subscription_status', 'is_active', 'updated_at'])
        
        # Guardar factura y pago
        payment = PayPalService.create_payment_record(
            user=user,
            tenant=tenant,
            amount=float(amount_str),
            capture_id=sale_id,
            order_id=sub_id,
        )
        Invoice.objects.create(
            user=user,
            tenant=tenant,
            amount=float(amount_str),
            due_date=now,
            is_paid=True,
            paid_at=now,
            payment_method='paypal',
            status='paid',
            stripe_payment_intent_id=sale_id,
            paypal_order_id=sub_id,
            payment=payment,
            description=f"PayPal Subscription {sub_id} - Sale {sale_id}",
        )
        
    logger.info("Processed sale %s for subscription %s, tenant extended to %s", sale_id, sub_id, access_until)


EVENT_HANDLERS = {
    'PAYMENT.CAPTURE.COMPLETED': handle_capture_completed,
    'PAYMENT.CAPTURE.DENIED': handle_capture_denied,
    'PAYMENT.CAPTURE.REFUNDED': handle_capture_refunded,
    'BILLING.SUBSCRIPTION.ACTIVATED': handle_subscription_activated,
    'BILLING.SUBSCRIPTION.CANCELLED': handle_subscription_cancelled,
    'PAYMENT.SALE.COMPLETED': handle_payment_sale_completed,
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
