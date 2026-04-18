from celery import shared_task
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import UserSubscription, Subscription
from apps.settings_api.policy_utils import should_auto_suspend_expired
import logging
import stripe
from stripe.error import StripeError
from html import escape

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)

logger = logging.getLogger(__name__)

def _email_branding_for_tenant(tenant):
    business_name = tenant.name or 'Auron Suite'
    logo_url = ''
    try:
        from apps.settings_api.barbershop_models import BarbershopSettings
        shop_settings = BarbershopSettings.objects.filter(tenant=tenant).first()
        if shop_settings:
            business_name = shop_settings.name or business_name
            if shop_settings.logo:
                raw_logo = shop_settings.logo.url
                frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:4200').rstrip('/')
                logo_url = f"{frontend_url}{raw_logo}" if raw_logo.startswith('/') else f"{frontend_url}/{raw_logo}"
    except Exception:
        pass
    return business_name, logo_url

def _build_html_email(tenant, title, message_lines):
    business_name, logo_url = _email_branding_for_tenant(tenant)
    logo_block = f'<img src="{escape(logo_url)}" alt="Logo" style="max-height:64px;max-width:180px;object-fit:contain;margin-bottom:12px;" />' if logo_url else ''
    list_block = ''.join([f'<p style="margin:0 0 10px 0;">{escape(line)}</p>' for line in message_lines])
    return f"""
    <div style="font-family:Arial,sans-serif;background:#f8fafc;padding:20px;">
      <div style="max-width:620px;margin:0 auto;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:24px;">
        <div style="text-align:center;border-bottom:1px solid #e5e7eb;padding-bottom:12px;margin-bottom:16px;">
          {logo_block}
          <h2 style="margin:0;color:#111827;">{escape(business_name)}</h2>
        </div>
        <h3 style="margin:0 0 12px 0;color:#111827;">{escape(title)}</h3>
        <div style="color:#374151;font-size:14px;line-height:1.6;">{list_block}</div>
      </div>
    </div>
    """

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def check_trial_expirations(self):
    """
    Task diario para verificar trials expirados
    Ejecutar diariamente a las 9:00 AM
    """
    try:
        if not should_auto_suspend_expired():
            logger.info("Auto suspension is disabled in system settings; skipping trial expiration check")
            return "Auto suspension disabled; skipped trial expiration check"

        today = timezone.now().date()
        
        # Buscar tenants con trial expirado
        expired_trials = Tenant.objects.filter(
            subscription_status='trial',
            trial_end_date__lt=today,
            is_active=True
        )
        
        suspended_count = 0
        for tenant in expired_trials:
            if not tenant.sync_subscription_state(save=True):
                continue
            
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
    except Exception as e:
        logger.error(f"Error checking trial expirations: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def cleanup_expired_trials(self):
    """
    Task para limpiar trials expirados y datos obsoletos
    Ejecutar semanalmente
    """
    try:
        today = timezone.now().date()
        
        # Limpiar tenants suspendidos por más de 30 días
        old_suspended = Tenant.objects.filter(
            subscription_status='suspended',
            updated_at__lt=today - timedelta(days=30)
        )
        
        cleaned_count = 0
        for tenant in old_suspended:
            if tenant.sync_subscription_state(save=True):
                cleaned_count += 1
            
            logger.info(f"Cleaned up old suspended tenant {tenant.name} (ID: {tenant.id})")
        
        return f"Cleaned up {cleaned_count} old suspended tenants"
    except Exception as e:
        logger.error(f"Error cleaning up expired trials: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_trial_expiration_warnings(self):
    """
    Task para enviar avisos de expiración próxima
    Ejecutar diariamente a las 10:00 AM
    """
    try:
        today = timezone.now().date()
        warning_dates = [
            today + timedelta(days=1),  # 1 día antes
            today + timedelta(days=3),  # 3 días antes
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
    except Exception as e:
        logger.error(f"Error sending trial warnings: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def check_expired_subscriptions(self):
    """Verificar y desactivar suscripciones expiradas"""
    try:
        if not should_auto_suspend_expired():
            logger.info("Auto suspension is disabled in system settings; skipping expired subscriptions check")
            return "Auto suspension disabled; skipped expired subscriptions check"

        expired_subs = UserSubscription.objects.filter(
            is_active=True,
            end_date__lt=timezone.now()
        )
        
        count = expired_subs.count()
        expired_subs.update(is_active=False)
        
        logger.info(f"Deactivated {count} expired subscriptions")
        return f'Deactivated {count} expired subscriptions'
    except Exception as e:
        logger.error(f"Error checking expired subscriptions: {str(e)}")
        raise self.retry(exc=e)

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
        html_message = _build_html_email(tenant, subject, [
            f"Hola {tenant.owner.full_name},",
            f"Tu prueba gratuita de 7 días para {tenant.name} ha expirado.",
            "Para continuar usando BarberSaaS inicia sesión y selecciona un plan de pago.",
            "No pierdas tus datos. Reactiva tu cuenta hoy."
        ])
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[tenant.contact_email],
            html_message=html_message,
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
        html_message = _build_html_email(tenant, subject, [
            f"Hola {tenant.owner.full_name},",
            f"Tu prueba gratuita de {tenant.name} expira en {days_remaining} días.",
            "Para evitar suspensión, entra a configuración de suscripción y elige un plan.",
            "No esperes al último momento."
        ])
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[tenant.contact_email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Error sending trial warning email to {tenant.contact_email}: {str(e)}")
