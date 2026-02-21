import stripe
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from apps.auth_api.models import User
from apps.subscriptions_api.models import UserSubscription
from apps.tenants_api.utils import get_active_tenant
from apps.billing_api.models import Invoice, PaymentAttempt
from apps.billing_api.reconciliation_models import ProcessedStripeEvent
from django.apps import apps
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Webhook idempotente con anti-replay para eventos de Stripe"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    # Validar firma de Stripe
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        logger.warning("Webhook rejected: Invalid payload")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.warning("Webhook rejected: Invalid signature")
        return HttpResponse(status=400)

    event_id = event['id']
    event_type = event['type']

    # IDEMPOTENCIA: Verificar si ya procesamos este evento
    if ProcessedStripeEvent.objects.filter(stripe_event_id=event_id).exists():
        logger.info(f"Event {event_id} already processed, skipping")
        return HttpResponse(status=200)

    # Procesar evento dentro de transacción atómica
    try:
        with transaction.atomic():
            # Registrar evento ANTES de procesarlo
            ProcessedStripeEvent.objects.create(
                stripe_event_id=event_id,
                event_type=event_type,
                payload=event['data']['object']
            )

            # Despachar a handler específico
            if event_type == 'invoice.payment_succeeded':
                handle_payment_succeeded(event['data']['object'])
            elif event_type == 'invoice.payment_failed':
                handle_payment_failed(event['data']['object'])
            elif event_type == 'customer.subscription.deleted':
                handle_subscription_cancelled(event['data']['object'])
            elif event_type == 'invoice.created':
                handle_invoice_created(event['data']['object'])

        logger.info(f"Event {event_id} processed successfully")
        return HttpResponse(status=200)

    except Exception as e:
        logger.error(f"Error processing event {event_id}: {str(e)}")
        # Rollback automático por transaction.atomic()
        return HttpResponse(status=500)


def handle_payment_succeeded(invoice_data):
    """Manejar pago exitoso con protección contra duplicados"""
    try:
        user_id = invoice_data['metadata'].get('user_id')
        payment_intent_id = invoice_data.get('payment_intent')
        
        if not user_id:
            logger.warning("Payment succeeded: missing user_id in metadata")
            return
        
        user = User.objects.get(id=user_id)
        
        # Validar tenant activo
        if hasattr(user, 'tenant') and user.tenant:
            try:
                get_active_tenant(user.tenant.id)
            except Exception as e:
                logger.warning(f"Payment succeeded for inactive tenant {user.tenant.id}: {str(e)}")
                return
        
        # Usar select_for_update para evitar race conditions
        with transaction.atomic():
            # Verificar si ya existe factura con este payment_intent
            existing = Invoice.objects.filter(
                stripe_payment_intent_id=payment_intent_id
            ).select_for_update().first()
            
            if existing:
                if existing.is_paid:
                    logger.info(f"Invoice for payment_intent {payment_intent_id} already marked as paid")
                    return
                # Actualizar factura existente
                existing.is_paid = True
                existing.paid_at = timezone.now()
                existing.payment_method = 'stripe'
                existing.status = 'paid'
                existing.save()
                invoice = existing
            else:
                # Crear nueva factura
                invoice = Invoice.objects.create(
                    user=user,
                    amount=invoice_data['amount_paid'] / 100,
                    due_date=timezone.now(),
                    is_paid=True,
                    paid_at=timezone.now(),
                    payment_method='stripe',
                    status='paid',
                    stripe_payment_intent_id=payment_intent_id,
                    description=f"Stripe Invoice {invoice_data.get('id', '')}"
                )
        
        # Reactivar tenant si estaba suspendido
        if hasattr(user, 'tenant') and user.tenant:
            tenant = user.tenant
            if tenant.subscription_status == 'suspended':
                tenant.subscription_status = 'active'
                tenant.is_active = True
                tenant.save()
                logger.info(f"Tenant {tenant.id} reactivated after payment")
                
    except User.DoesNotExist:
        logger.warning(f"Payment succeeded: user {user_id} not found")
    except Exception as e:
        logger.error(f"Error handling payment succeeded: {str(e)}")
        raise  # Re-raise para rollback


def handle_payment_failed(invoice_data):
    """Manejar pago fallido"""
    try:
        user_id = invoice_data['metadata'].get('user_id')
        if not user_id:
            logger.warning("Payment failed: missing user_id in metadata")
            return
        
        user = User.objects.get(id=user_id)
        
        # Validar tenant activo
        if hasattr(user, 'tenant') and user.tenant:
            try:
                get_active_tenant(user.tenant.id)
            except Exception as e:
                logger.warning(f"Payment failed for inactive tenant {user.tenant.id}: {str(e)}")
                return
        
        # Registrar intento fallido
        PaymentAttempt.objects.create(
            invoice_id=invoice_data.get('id'),
            success=False,
            status='failed',
            message=f"Payment failed: {invoice_data.get('failure_reason', 'Unknown')}"
        )
        
        # Suspender tenant después de 3 intentos fallidos
        failed_attempts = PaymentAttempt.objects.filter(
            invoice__user=user,
            success=False
        ).count()
        
        if failed_attempts >= 3 and hasattr(user, 'tenant'):
            tenant = user.tenant
            tenant.subscription_status = 'suspended'
            tenant.is_active = False
            tenant.save()
            logger.warning(f"Tenant {tenant.id} suspended after {failed_attempts} failed payments")
            
    except User.DoesNotExist:
        logger.warning(f"Payment failed: user {user_id} not found")
    except Exception as e:
        logger.error(f"Error handling payment failed: {str(e)}")
        raise


def handle_subscription_cancelled(subscription_data):
    """Manejar cancelación de suscripción"""
    try:
        user_id = subscription_data['metadata'].get('user_id')
        if not user_id:
            logger.warning("Subscription cancelled: missing user_id in metadata")
            return
        
        user = User.objects.get(id=user_id)
        
        # Validar tenant activo
        if hasattr(user, 'tenant') and user.tenant:
            try:
                get_active_tenant(user.tenant.id)
            except Exception as e:
                logger.warning(f"Subscription cancelled for inactive tenant {user.tenant.id}: {str(e)}")
                return
        
        # Actualizar suscripción local
        UserSubscription.objects.filter(user=user, is_active=True).update(
            is_active=False,
            end_date=timezone.now()
        )
        
        # Actualizar tenant
        if hasattr(user, 'tenant'):
            tenant = user.tenant
            tenant.subscription_status = 'cancelled'
            tenant.is_active = False
            tenant.save()
            logger.info(f"Tenant {tenant.id} cancelled subscription")
            
    except User.DoesNotExist:
        logger.warning(f"Subscription cancelled: user {user_id} not found")
    except Exception as e:
        logger.error(f"Error handling subscription cancelled: {str(e)}")
        raise


def handle_invoice_created(invoice_data):
    """Manejar creación de factura"""
    try:
        user_id = invoice_data['metadata'].get('user_id')
        if not user_id:
            logger.warning("Invoice created: missing user_id in metadata")
            return
        
        user = User.objects.get(id=user_id)
        
        # Validar tenant activo
        if hasattr(user, 'tenant') and user.tenant:
            try:
                get_active_tenant(user.tenant.id)
            except Exception as e:
                logger.warning(f"Invoice created for inactive tenant {user.tenant.id}: {str(e)}")
                return
        
        Invoice.objects.get_or_create(
            user=user,
            amount=invoice_data['amount_due'] / 100,
            defaults={
                'due_date': timezone.datetime.fromtimestamp(
                    invoice_data['due_date'], tz=timezone.utc
                ),
                'description': f"Subscription - {invoice_data.get('description', '')}",
                'status': 'pending'
            }
        )
        
    except User.DoesNotExist:
        logger.warning(f"Invoice created: user {user_id} not found")
    except Exception as e:
        logger.error(f"Error handling invoice created: {str(e)}")
        raise
