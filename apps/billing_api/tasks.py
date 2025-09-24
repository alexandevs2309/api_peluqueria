from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import UserSubscription
from django.apps import apps
from .stripe_service import StripeService
from apps.settings_api.models import SystemSettings

@shared_task
def check_expired_subscriptions():
    """Tarea para verificar y suspender suscripciones vencidas"""
    Invoice = apps.get_model('billing_api', 'Invoice')
    PaymentAttempt = apps.get_model('billing_api', 'PaymentAttempt')
    system_settings = SystemSettings.get_settings()
    
    if not system_settings.auto_suspend_expired:
        return "Auto-suspensión deshabilitada"
    
    now = timezone.now()
    expired_count = 0
    
    # Buscar suscripciones vencidas que aún están activas
    expired_subscriptions = UserSubscription.objects.filter(
        end_date__lt=now,
        is_active=True
    )
    
    for subscription in expired_subscriptions:
        try:
            # Desactivar suscripción
            subscription.is_active = False
            subscription.save()
            
            # Suspender tenant
            if hasattr(subscription.user, 'tenant') and subscription.user.tenant:
                tenant = subscription.user.tenant
                tenant.subscription_status = 'suspended'
                tenant.save()
                
                expired_count += 1
                
        except Exception as e:
            print(f"Error suspendiendo suscripción {subscription.id}: {str(e)}")
    
    return f"Suspendidas {expired_count} suscripciones vencidas"

@shared_task
def check_failed_payments():
    """Tarea para verificar pagos fallidos y suspender clientes morosos"""
    Invoice = apps.get_model('billing_api', 'Invoice')
    PaymentAttempt = apps.get_model('billing_api', 'PaymentAttempt')
    system_settings = SystemSettings.get_settings()
    
    if not system_settings.auto_suspend_expired:
        return "Auto-suspensión deshabilitada"
    
    # Buscar facturas vencidas no pagadas (más de 7 días)
    grace_period = timezone.now() - timedelta(days=7)
    overdue_invoices = Invoice.objects.filter(
        due_date__lt=grace_period,
        is_paid=False,
        status='pending'
    )
    
    suspended_count = 0
    
    for invoice in overdue_invoices:
        try:
            # Contar intentos de pago fallidos
            failed_attempts = PaymentAttempt.objects.filter(
                invoice=invoice,
                success=False
            ).count()
            
            # Suspender después de 3 intentos fallidos o 7 días de mora
            if failed_attempts >= 3 or invoice.due_date < grace_period:
                # Actualizar factura
                invoice.status = 'failed'
                invoice.save()
                
                # Suspender tenant
                if hasattr(invoice.user, 'tenant') and invoice.user.tenant:
                    tenant = invoice.user.tenant
                    if tenant.subscription_status != 'suspended':
                        tenant.subscription_status = 'suspended'
                        tenant.save()
                        
                        # Suspender en Stripe si está habilitado
                        if system_settings.stripe_enabled:
                            try:
                                StripeService.suspend_customer(invoice.user.email)
                            except Exception as e:
                                print(f"Error suspendiendo en Stripe: {str(e)}")
                        
                        suspended_count += 1
                        
        except Exception as e:
            print(f"Error procesando factura {invoice.id}: {str(e)}")
    
    return f"Suspendidos {suspended_count} clientes morosos"

@shared_task
def send_payment_reminders():
    """Enviar recordatorios de pago a clientes con facturas vencidas"""
    Invoice = apps.get_model('billing_api', 'Invoice')
    from apps.settings_api.integration_service import IntegrationService
    
    # Facturas vencidas hace 1-3 días (recordatorio temprano)
    reminder_date = timezone.now() - timedelta(days=1)
    final_reminder_date = timezone.now() - timedelta(days=3)
    
    pending_invoices = Invoice.objects.filter(
        due_date__range=[final_reminder_date, reminder_date],
        is_paid=False,
        status='pending'
    )
    
    sent_count = 0
    
    for invoice in pending_invoices:
        try:
            if IntegrationService.is_sendgrid_enabled():
                # Enviar email de recordatorio
                subject = f"Recordatorio de pago - Factura #{invoice.id}"
                message = f"""
                Estimado {invoice.user.full_name},
                
                Su factura #{invoice.id} por ${invoice.amount} está vencida.
                Fecha de vencimiento: {invoice.due_date.strftime('%d/%m/%Y')}
                
                Por favor, realice el pago lo antes posible para evitar la suspensión del servicio.
                
                Gracias,
                Equipo BarberSaaS
                """
                
                IntegrationService.send_email(
                    invoice.user.email,
                    subject,
                    message
                )
                sent_count += 1
                
        except Exception as e:
            print(f"Error enviando recordatorio para factura {invoice.id}: {str(e)}")
    
    return f"Enviados {sent_count} recordatorios de pago"