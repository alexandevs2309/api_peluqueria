import stripe
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.conf import settings
from django.utils import timezone
from apps.auth_api.models import User
from apps.subscriptions_api.models import UserSubscription
from apps.tenants_api.models import Tenant
from django.apps import apps

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Webhook para manejar eventos de Stripe"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
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
        if user_id:
            user = User.objects.get(id=user_id)
            
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
                    tenant.save()
                    
    except User.DoesNotExist:
        pass

def handle_payment_failed(invoice_data):
    """Manejar pago fallido"""
    PaymentAttempt = apps.get_model('billing_api', 'PaymentAttempt')
    try:
        user_id = invoice_data['metadata'].get('user_id')
        if user_id:
            user = User.objects.get(id=user_id)
            
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
                tenant.save()
                
    except User.DoesNotExist:
        pass

def handle_subscription_cancelled(subscription_data):
    """Manejar cancelación de suscripción"""
    try:
        user_id = subscription_data['metadata'].get('user_id')
        if user_id:
            user = User.objects.get(id=user_id)
            
            # Actualizar suscripción local
            UserSubscription.objects.filter(user=user, is_active=True).update(
                is_active=False,
                end_date=timezone.now()
            )
            
            # Actualizar tenant
            if hasattr(user, 'tenant'):
                tenant = user.tenant
                tenant.subscription_status = 'cancelled'
                tenant.save()
                
    except User.DoesNotExist:
        pass

def handle_invoice_created(invoice_data):
    """Manejar creación de factura"""
    Invoice = apps.get_model('billing_api', 'Invoice')
    try:
        user_id = invoice_data['metadata'].get('user_id')
        if user_id:
            user = User.objects.get(id=user_id)
            
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
        pass