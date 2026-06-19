from celery import shared_task
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from apps.tenants_api.models import Tenant
from apps.tenants_api.subscription_lifecycle import sync_subscription_state
from apps.subscriptions_api.models import UserSubscription, Subscription
from apps.settings_api.policy_utils import should_auto_suspend_expired
import logging
import stripe
from stripe import StripeError

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
    from apps.emails.service import EmailRenderer
    business_name, logo_url = _email_branding_for_tenant(tenant)
    content = ''.join(f'<p style="margin:0 0 8px;">{line}</p>' for line in message_lines)
    return EmailRenderer.render('trial_content.html', {
        'business_name': business_name,
        'logo_url': logo_url,
        'title': title,
        'content': content,
        'user_full_name': tenant.owner.full_name if tenant.owner else '',
    })

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def daily_subscription_check(self):
    """
    Task diaria para normalizar lifecycle de suscripciones.
    Pensada para Celery beat o cron.
    """
    try:
        now = timezone.now()
        processed = 0

        tenants = Tenant.objects.filter(deleted_at__isnull=True).order_by('id')
        for tenant in tenants.iterator():
            result = sync_subscription_state(tenant, now=now, save=True)
            if result.changed:
                processed += 1
                logger.info(
                    "Subscription lifecycle synced tenant=%s status=%s reasons=%s",
                    tenant.id,
                    tenant.subscription_status,
                    ", ".join(result.reasons),
                )

        logger.info("Daily subscription check processed %s tenants", processed)
        return f"Processed {processed} tenant subscription transitions"
    except Exception as e:
        logger.error(f"Error running daily subscription check: {str(e)}")
        raise self.retry(exc=e)

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
            is_active=True,
            deleted_at__isnull=True,
        )
        
        suspended_count = 0
        for tenant in expired_trials:
            result = sync_subscription_state(tenant, save=True)
            if not result.changed:
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
            updated_at__lt=today - timedelta(days=30),
            deleted_at__isnull=True,
        )
        
        cleaned_count = 0
        for tenant in old_suspended:
            result = sync_subscription_state(tenant, save=True)
            if result.changed:
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
def send_subscription_expiry_warnings(self):
    """
    Task diaria para enviar avisos de expiración de suscripciones pagadas.
    Envía correos a 7, 3 y 1 día antes de que expire el acceso pago.
    """
    try:
        today = timezone.now().date()
        warned_count = 0

        # Tenants con suscripción activa y fecha de expiración definida
        tenants = Tenant.objects.filter(
            subscription_status='active',
            access_until__isnull=False,
            is_active=True,
            deleted_at__isnull=True,
        ).select_related('owner', 'subscription_plan')

        for tenant in tenants:
            access_date = tenant.access_until.date()
            days_remaining = (access_date - today).days

            # Solo procesar hitos: 7, 3, 1 día(s)
            if days_remaining not in (7, 3, 1):
                continue

            notification_key = f'expiry_warning_{days_remaining}d'

            # Verificar si ya se envió este aviso
            billing_info = dict(getattr(tenant, 'billing_info', None) or {})
            warnings_sent = billing_info.get('subscription_warnings_sent') or {}

            if warnings_sent.get(notification_key):
                logger.info(
                    "send_subscription_expiry_warnings: already sent tenant=%s key=%s",
                    tenant.subdomain,
                    notification_key,
                )
                continue

            # Enviar email
            _send_subscription_expiry_email(tenant, days_remaining)

            # Marcar como enviado
            warnings_sent[notification_key] = True
            billing_info['subscription_warnings_sent'] = warnings_sent
            tenant.billing_info = billing_info
            tenant.save(update_fields=['billing_info'])

            warned_count += 1
            logger.info(
                "Sent subscription expiry warning to %s (%d days remaining)",
                tenant.subdomain,
                days_remaining,
            )

        logger.info("send_subscription_expiry_warnings: sent %s warnings", warned_count)
        return f"Sent {warned_count} subscription expiry warnings"
    except Exception as e:
        logger.error("Error sending subscription expiry warnings: %s", str(e))
        raise self.retry(exc=e)


def _send_subscription_expiry_email(tenant, days_remaining):
    """Enviar email de aviso de expiración de suscripción paga."""
    from apps.auth_api.tasks import send_email_async

    owner = tenant.owner
    recipient = getattr(owner, 'email', None) or getattr(tenant, 'contact_email', None)
    if not recipient:
        logger.warning(
            "_send_subscription_expiry_email: tenant %s has no recipient email",
            tenant.id,
        )
        return

    plan_name = tenant.subscription_plan.name if tenant.subscription_plan else 'Plan'
    expiry_date = tenant.access_until.strftime('%d/%m/%Y')

    if days_remaining == 1:
        subject = f"Tu suscripción expira mañana - {tenant.name}"
        days_text = "mañana"
    else:
        subject = f"Tu suscripción expira en {days_remaining} días - {tenant.name}"
        days_text = f"{days_remaining} días"

    message = f"""
    Hola {owner.full_name or owner.email},

    Tu suscripción del plan {plan_name} para {tenant.name} expira en {days_text}.

    Fecha de expiración: {expiry_date}

    Para renovar tu suscripción y seguir usando Auron Suite sin interrupción:
    1. Inicia sesión en tu cuenta
    2. Ve a Configuración > Suscripción o haz clic en el enlace de abajo
    3. Renueva tu plan

    Enlace directo: https://auronsuite.com/client/payment

    ¡No pierdas el acceso a tus datos y sigue disfrutando de Auron Suite!

    El equipo de Auron Suite
    """

    try:
        html_message = _build_html_email(tenant, subject, [
            f"Hola {owner.full_name or owner.email},",
            f"Tu suscripción del plan {plan_name} para {tenant.name} expira en {days_text}.",
            f"Fecha de expiración: {expiry_date}",
            "Para renovar, inicia sesión y ve a Configuración > Suscripción.",
            '<a href="https://auronsuite.com/client/payment" style="display:inline-block;padding:12px 24px;background-color:#3B82F6;color:#ffffff;text-decoration:none;border-radius:6px;font-weight:bold;">Renovar Suscripción</a>',
            "No pierdas el acceso a tus datos.",
        ])
        send_email_async.delay(
            subject=subject,
            message=message,
            from_email='',
            recipient_list=[recipient],
            html_message=html_message,
        )
    except Exception as e:
        logger.error(
            "Error sending subscription expiry email to %s: %s",
            recipient,
            str(e),
        )


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
    from apps.auth_api.tasks import send_email_async

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
        send_email_async.delay(
            subject=subject,
            message=message,
            from_email='',
            recipient_list=[tenant.contact_email],
            html_message=html_message,
        )
    except Exception as e:
        logger.error(f"Error sending trial expired email to {tenant.contact_email}: {str(e)}")

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_trial_warning_email(self, tenant_id=None, days_remaining=None, days_left=None):
    """Enviar email de aviso antes de que expire el trial"""
    if days_remaining is None:
        days_remaining = days_left

    if isinstance(tenant_id, Tenant):
        tenant = tenant_id
    else:
        try:
            tenant = Tenant.objects.select_related('owner').get(id=tenant_id)
        except Tenant.DoesNotExist:
            logger.warning("send_trial_warning_email: tenant %s not found", tenant_id)
            return

    owner = tenant.owner
    recipient = getattr(owner, 'email', None) or getattr(tenant, 'contact_email', None)
    if not recipient:
        logger.warning("send_trial_warning_email: tenant %s has no recipient email", tenant.id)
        return

    notification_key = f'trial_warning_{days_remaining}d'
    if getattr(tenant, 'trial_notifications_sent', None) and tenant.trial_notifications_sent.get(notification_key):
        logger.info(
            "send_trial_warning_email: already sent tenant=%s days=%s",
            tenant.subdomain,
            days_remaining,
        )
        return

    subject = f"Tu prueba gratuita expira en {days_remaining} días - {tenant.name}"
    message = f"""
    Hola {owner.full_name or owner.email},
    
    Tu prueba gratuita de {tenant.name} expira en {days_remaining} días.
    
    Para evitar la suspensión de tu cuenta:
    1. Inicia sesión en tu cuenta
    2. Ve a Configuración > Suscripción  
    3. Selecciona un plan de pago
    
    ¡No esperes hasta el último momento!
    
    El equipo de BarberSaaS
    """
    
    try:
        from apps.auth_api.tasks import send_email_async

        html_message = _build_html_email(tenant, subject, [
            f"Hola {owner.full_name or owner.email},",
            f"Tu prueba gratuita de {tenant.name} expira en {days_remaining} días.",
            "Para evitar suspensión, entra a configuración de suscripción y elige un plan.",
            "No esperes al último momento."
        ])
        send_email_async.delay(
            subject=subject,
            message=message,
            from_email='',
            recipient_list=[recipient],
            html_message=html_message,
        )

        if getattr(tenant, 'trial_notifications_sent', None) is not None:
            tenant.trial_notifications_sent[notification_key] = True
            tenant.save(update_fields=['trial_notifications_sent'])
    except Exception as e:
        logger.error(f"Error sending trial warning email to {recipient}: {str(e)}")
        raise self.retry(exc=e)
