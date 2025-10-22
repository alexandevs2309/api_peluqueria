from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import UserSubscription
import logging

logger = logging.getLogger(__name__)

@shared_task
def check_trial_expirations():
    """
    Task diario para verificar trials expirados
    Ejecutar diariamente a las 9:00 AM
    """
    today = timezone.now().date()
    
    # Buscar tenants con trial expirado
    expired_trials = Tenant.objects.filter(
        subscription_status='trial',
        trial_end_date__lt=today,
        is_active=True
    )
    
    suspended_count = 0
    for tenant in expired_trials:
        # Suspender tenant
        tenant.subscription_status = 'suspended'
        tenant.is_active = False
        tenant.save()
        
        # Desactivar suscripción del usuario
        UserSubscription.objects.filter(
            user=tenant.owner,
            is_active=True
        ).update(is_active=False)
        
        # Enviar email de notificación
        send_trial_expired_email(tenant)
        suspended_count += 1
        
        logger.info(f"Trial expired for tenant {tenant.name} (ID: {tenant.id})")
    
    logger.info(f"Processed {suspended_count} expired trials")
    return f"Suspended {suspended_count} tenants with expired trials"

@shared_task
def cleanup_expired_trials():
    """
    Task para limpiar trials expirados y datos obsoletos
    Ejecutar semanalmente
    """
    today = timezone.now().date()
    
    # Limpiar tenants suspendidos por más de 30 días
    old_suspended = Tenant.objects.filter(
        subscription_status='suspended',
        updated_at__lt=today - timezone.timedelta(days=30)
    )
    
    cleaned_count = 0
    for tenant in old_suspended:
        # Marcar como inactivo permanentemente
        tenant.is_active = False
        tenant.save()
        cleaned_count += 1
        
        logger.info(f"Cleaned up old suspended tenant {tenant.name} (ID: {tenant.id})")
    
    return f"Cleaned up {cleaned_count} old suspended tenants"

@shared_task
def send_trial_expiration_warnings():
    """
    Task para enviar avisos de expiración próxima
    Ejecutar diariamente a las 10:00 AM
    """
    today = timezone.now().date()
    warning_dates = [
        today + timezone.timedelta(days=1),  # 1 día antes
        today + timezone.timedelta(days=3),  # 3 días antes
    ]
    
    warned_count = 0
    for warning_date in warning_dates:
        tenants_to_warn = Tenant.objects.filter(
            subscription_status='trial',
            trial_end_date=warning_date,
            is_active=True
        )
        
        for tenant in tenants_to_warn:
            days_remaining = (tenant.trial_end_date - today).days
            send_trial_warning_email(tenant, days_remaining)
            warned_count += 1
            
            logger.info(f"Sent trial warning to {tenant.name} ({days_remaining} days remaining)")
    
    return f"Sent {warned_count} trial expiration warnings"

def send_trial_expired_email(tenant):
    """Enviar email cuando el trial expira"""
    subject = f"Tu prueba gratuita ha expirado - {tenant.name}"
    message = f"""
    Hola {tenant.owner.full_name},
    
    Tu prueba gratuita de 7 días para {tenant.name} ha expirado.
    
    Para continuar usando BarberSaaS:
    1. Inicia sesión en tu cuenta
    2. Ve a Configuración > Suscripción
    3. Selecciona un plan de pago
    
    ¡No pierdas tus datos! Reactiva tu cuenta hoy.
    
    El equipo de BarberSaaS
    """
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[tenant.contact_email],
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Error sending trial expired email to {tenant.contact_email}: {str(e)}")

def send_trial_warning_email(tenant, days_remaining):
    """Enviar email de aviso antes de que expire el trial"""
    subject = f"Tu prueba gratuita expira en {days_remaining} días - {tenant.name}"
    message = f"""
    Hola {tenant.owner.full_name},
    
    Tu prueba gratuita de {tenant.name} expira en {days_remaining} días.
    
    Para evitar la suspensión de tu cuenta:
    1. Inicia sesión en tu cuenta
    2. Ve a Configuración > Suscripción  
    3. Selecciona un plan de pago
    
    ¡No esperes hasta el último momento!
    
    El equipo de BarberSaaS
    """
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[tenant.contact_email],
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Error sending trial warning email to {tenant.contact_email}: {str(e)}")