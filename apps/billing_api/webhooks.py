import stripe
import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.conf import settings
from django.utils import timezone
from apps.auth_api.models import User
from apps.subscriptions_api.models import UserSubscription
from apps.tenants_api.models import Tenant
from apps.tenants_api.utils import get_active_tenant
from django.apps import apps
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Webhook para manejar eventos de Stripe"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    # ✅ HARDENING: Validar firma de Stripe
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        logger.warning(f"Webhook rejected: Invalid payload - {str(e)}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.warning(f"Webhook rejected: Invalid signature - {str(e)}")
        return HttpResponse(status=400)

    # Manejar eventos
    if event['type'] == 'invoice.payment_succeeded':
        handle_payment_succeeded(event['data']['object'])
    elif event['type'] == 'invoice.payment_failed':
        handle_payment_failed(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_cancelled(event['data']['object'])
    elif event['type'] == 'invoice.created':
        handle_invoice_created(event['data']['object'])

    return HttpResponse(status=200)

def handle_payment_succeeded(invoice_data):
    """Manejar pago exitoso"""
    Invoice = apps.get_model('billing_api', 'Invoice')
    try:
        user_id = invoice_data['metadata'].get('user_id')
        if not user_id:
            logger.warning("Payment succeeded webhook: missing user_id in metadata")
            return
        
        user = User.objects.get(id=user_id)
        
        # ✅ HARDENING: Validar que tenant esté activo
        if hasattr(user, 'tenant') and user.tenant:
            try:
                tenant = get_active_tenant(user.tenant.id)
            except Exception as e:
                logger.warning(f"Payment succeeded for inactive tenant {user.tenant.id}: {str(e)}")
                return  # Abortar si tenant está eliminado
        
        # Actualizar factura local
        invoice, created = Invoice.objects.get_or_create(
            user=user,
            amount=invoice_data['amount_paid'] / 100,  # Stripe usa centavos
            defaults={
                'is_paid': True,
                'paid_at': timezone.now(),
                'payment_method': 'stripe',
                'status': 'paid'
            }
        )
        
        # Reactivar tenant si estaba suspendido
        if hasattr(user, 'tenant') and user.tenant:
            tenant = user.tenant
            if tenant.subscription_status == 'suspended':
                tenant.subscription_status = 'active'
                tenant.is_active = True  # ✅ Reactivar tenant
                tenant.save()
                logger.info(f"Tenant {tenant.id} reactivated after payment")
                
    except User.DoesNotExist:
        logger.warning(f"Payment succeeded webhook: user {user_id} not found")
    except Exception as e:
        logger.error(f"Error handling payment succeeded: {str(e)}")

def handle_payment_failed(invoice_data):
    """Manejar pago fallido"""
    PaymentAttempt = apps.get_model('billing_api', 'PaymentAttempt')
    try:
        user_id = invoice_data['metadata'].get('user_id')
        if not user_id:
            logger.warning("Payment failed webhook: missing user_id in metadata")
            return
        
        user = User.objects.get(id=user_id)
        
        # ✅ HARDENING: Validar que tenant esté activo antes de procesar
        if hasattr(user, 'tenant') and user.tenant:
            try:
                tenant = get_active_tenant(user.tenant.id)
            except Exception as e:
                logger.warning(f"Payment failed for inactive tenant {user.tenant.id}: {str(e)}")
                return  # Abortar si tenant está eliminado
        
        # Crear registro de intento fallido
        PaymentAttempt.objects.create(
            invoice_id=invoice_data.get('id'),
            success=False,
            status='failed',
            message=f"Pago fallido: {invoice_data.get('failure_reason', 'Unknown')}"
        )
        
        # Suspender tenant después de 3 intentos fallidos
        failed_attempts = PaymentAttempt.objects.filter(
            invoice__user=user,
            success=False
        ).count()
        
        if failed_attempts >= 3 and hasattr(user, 'tenant'):
            tenant = user.tenant
            tenant.subscription_status = 'suspended'
            tenant.is_active = False  # ✅ Desactivar tenant
            tenant.save()
            logger.warning(f"Tenant {tenant.id} suspended after {failed_attempts} failed payments")
            
    except User.DoesNotExist:
        logger.warning(f"Payment failed webhook: user {user_id} not found")
    except Exception as e:
        logger.error(f"Error handling payment failed: {str(e)}")

def handle_subscription_cancelled(subscription_data):
    """Manejar cancelación de suscripción"""
    try:
        user_id = subscription_data['metadata'].get('user_id')
        if not user_id:
            logger.warning("Subscription cancelled webhook: missing user_id in metadata")
            return
        
        user = User.objects.get(id=user_id)
        
        # ✅ HARDENING: Validar que tenant esté activo
        if hasattr(user, 'tenant') and user.tenant:
            try:
                tenant = get_active_tenant(user.tenant.id)
            except Exception as e:
                logger.warning(f"Subscription cancelled for inactive tenant {user.tenant.id}: {str(e)}")
                return  # Abortar si tenant está eliminado
        
        # Actualizar suscripción local
        UserSubscription.objects.filter(user=user, is_active=True).update(
            is_active=False,
            end_date=timezone.now()
        )
        
        # Actualizar tenant
        if hasattr(user, 'tenant'):
            tenant = user.tenant
            tenant.subscription_status = 'cancelled'
            tenant.is_active = False  # ✅ Desactivar tenant
            tenant.save()
            logger.info(f"Tenant {tenant.id} cancelled subscription")
            
    except User.DoesNotExist:
        logger.warning(f"Subscription cancelled webhook: user {user_id} not found")
    except Exception as e:
        logger.error(f"Error handling subscription cancelled: {str(e)}")

def handle_invoice_created(invoice_data):
    """Manejar creación de factura"""
    Invoice = apps.get_model('billing_api', 'Invoice')
    try:
        user_id = invoice_data['metadata'].get('user_id')
        if not user_id:
            logger.warning("Invoice created webhook: missing user_id in metadata")
            return
        
        user = User.objects.get(id=user_id)
        
        # ✅ HARDENING: Validar que tenant esté activo
        if hasattr(user, 'tenant') and user.tenant:
            try:
                tenant = get_active_tenant(user.tenant.id)
            except Exception as e:
                logger.warning(f"Invoice created for inactive tenant {user.tenant.id}: {str(e)}")
                return  # Abortar si tenant está eliminado
        
        Invoice.objects.get_or_create(
            user=user,
            amount=invoice_data['amount_due'] / 100,
            defaults={
                'due_date': timezone.datetime.fromtimestamp(
                    invoice_data['due_date'], tz=timezone.utc
                ),
                'description': f"Suscripción - {invoice_data.get('description', '')}",
                'status': 'pending'
            }
        )
        
    except User.DoesNotExist:
        logger.warning(f"Invoice created webhook: user {user_id} not found")
    except Exception as e:
        logger.error(f"Error handling invoice created: {str(e)}")