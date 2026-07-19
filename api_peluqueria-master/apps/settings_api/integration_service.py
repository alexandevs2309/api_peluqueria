from django.conf import settings as django_settings
from .models import SystemSettings
import os
import logging

logger = logging.getLogger(__name__)


class IntegrationService:
    """Servicio para manejar integraciones basado en feature toggles"""

    @staticmethod
    def _setting_or_env(system_value, env_name, settings_attr=None, default=''):
        if system_value:
            return system_value
        env_value = os.getenv(env_name)
        if env_value:
            return env_value
        if settings_attr:
            return getattr(django_settings, settings_attr, default) or default
        return default

    @staticmethod
    def get_system_settings():
        """Obtener configuraciones del sistema"""
        return SystemSettings.get_settings()

    @staticmethod
    def is_stripe_enabled():
        """Verificar si Stripe esta habilitado y configurado correctamente"""
        system_settings = IntegrationService.get_system_settings()
        secret_key = system_settings.stripe_secret_key or os.getenv('STRIPE_SECRET_KEY')
        public_key = system_settings.stripe_public_key or os.getenv('STRIPE_PUBLISHABLE_KEY')

        if not system_settings.stripe_enabled:
            return False

        if not secret_key or not public_key:
            return False

        if not secret_key.startswith('sk_'):
            return False

        if not public_key.startswith('pk_'):
            return False

        return True

    @staticmethod
    def is_paypal_enabled():
        """Verificar si PayPal esta habilitado"""
        system_settings = IntegrationService.get_system_settings()
        client_id = system_settings.paypal_client_id or os.getenv('PAYPAL_CLIENT_ID')
        client_secret = system_settings.paypal_client_secret or os.getenv('PAYPAL_SECRET')
        return system_settings.paypal_enabled and bool(client_id) and bool(client_secret)

    @staticmethod
    def is_twilio_enabled():
        """Verificar si Twilio (SMS) esta habilitado"""
        system_settings = IntegrationService.get_system_settings()
        account_sid = system_settings.twilio_account_sid or os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = system_settings.twilio_auth_token or os.getenv('TWILIO_AUTH_TOKEN')
        return system_settings.twilio_enabled and bool(account_sid) and bool(auth_token)

    @staticmethod
    def is_sendgrid_enabled():
        """[DEPRECATED] Usar is_email_enabled()"""
        return IntegrationService.is_email_enabled()

    @staticmethod
    def is_email_enabled():
        system_settings = IntegrationService.get_system_settings()
        has_smtp_db = bool(system_settings.smtp_host and system_settings.smtp_username and system_settings.smtp_password)
        has_smtp_env = bool(os.getenv('EMAIL_HOST') and os.getenv('EMAIL_HOST_USER') and os.getenv('EMAIL_HOST_PASSWORD'))
        has_resend = bool(os.getenv('RESEND_API_KEY', '').startswith('re_'))
        return has_smtp_db or has_smtp_env or has_resend

    @staticmethod
    def is_aws_s3_enabled():
        """Verificar si AWS S3 esta habilitado"""
        system_settings = IntegrationService.get_system_settings()
        return (
            system_settings.aws_s3_enabled
            and bool(os.getenv('AWS_ACCESS_KEY_ID'))
            and bool(os.getenv('AWS_SECRET_ACCESS_KEY'))
            and bool(os.getenv('AWS_STORAGE_BUCKET_NAME'))
        )

    @staticmethod
    def is_cloudinary_enabled():
        """Verificar si Cloudinary esta habilitado para media storage"""
        return bool(
            getattr(django_settings, 'USE_CLOUDINARY', False)
            and os.getenv('CLOUDINARY_CLOUD_NAME')
            and os.getenv('CLOUDINARY_API_KEY')
            and os.getenv('CLOUDINARY_API_SECRET')
        )

    @staticmethod
    def get_integration_status():
        """Obtener estado de todas las integraciones"""
        return {
            'stripe': IntegrationService.is_stripe_enabled(),
            'paypal': IntegrationService.is_paypal_enabled(),
            'twilio': IntegrationService.is_twilio_enabled(),
            'email': IntegrationService.is_email_enabled(),
            'aws_s3': IntegrationService.is_aws_s3_enabled(),
            'cloudinary': IntegrationService.is_cloudinary_enabled(),
        }

    @staticmethod
    def send_sms(phone, message):
        """Enviar SMS si Twilio esta habilitado"""
        if not IntegrationService.is_twilio_enabled():
            raise Exception("Twilio no esta habilitado")

        system_settings = IntegrationService.get_system_settings()
        account_sid = system_settings.twilio_account_sid or os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = system_settings.twilio_auth_token or os.getenv('TWILIO_AUTH_TOKEN')
        from_number = system_settings.twilio_phone_number or os.getenv('TWILIO_PHONE_NUMBER')

        if not all([account_sid, auth_token, from_number]):
            raise Exception("Twilio no está completamente configurado")

        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            resp = client.messages.create(
                body=message,
                from_=from_number,
                to=phone
            )
            logger.info("SMS sent to %s: sid=%s", phone, resp.sid)
            return resp.sid
        except Exception as e:
            logger.error("Error sending SMS to %s: %s", phone, str(e))
            from apps.audit_api.views import AuditLogViewSet
            AuditLogViewSet.log_integration_error('Twilio', f"Error enviando SMS: {str(e)}")
            raise Exception(f"Error enviando SMS: {str(e)}")

    @staticmethod
    def send_whatsapp(phone, message, tenant=None):
        """Enviar WhatsApp si está habilitado (por QR o por Twilio fallback)"""
        override = getattr(django_settings, 'DEV_WHATSAPP_OVERRIDE', '')
        original = phone
        if override:
            phone = override
            logger.info("DEV_WHATSAPP_OVERRIDE activo: redirigiendo de %s a %s", original, phone)
            # Si hay override, intentar usar cualquier tenant con WhatsApp conectado
            if not tenant:
                from apps.settings_api.models import BarbershopSettings
                try:
                    qr_settings = BarbershopSettings.objects.filter(
                        whatsapp_enabled=True,
                        whatsapp_status='connected'
                    ).select_related('tenant').first()
                    if qr_settings:
                        tenant = qr_settings.tenant
                        logger.info("DEV_WHATSAPP_OVERRIDE: usando tenant %s para envío QR", tenant.subdomain)
                except Exception:
                    pass
        # 1. Comprobar si el tenant tiene configurada su pasarela QR
        if tenant:
            from apps.settings_api.models import BarbershopSettings
            try:
                settings = tenant.barbershop_settings
                if settings.whatsapp_enabled and settings.whatsapp_status == 'connected' and settings.whatsapp_instance_name:
                    from apps.settings_api.whatsapp_provider import get_whatsapp_provider
                    provider = get_whatsapp_provider()
                    # Enviar vía QR
                    try:
                        provider.send_message(
                            instance_name=settings.whatsapp_instance_name,
                            token=settings.whatsapp_token,
                            to_phone=phone,
                            message=message
                        )
                        logger.info("WhatsApp QR sent to %s for tenant %s", phone, tenant.subdomain)
                        return "success_qr"
                    except Exception as e:
                        logger.error("Error sending WhatsApp QR to %s for tenant %s: %s", phone, tenant.subdomain, str(e))
                        raise e
            except BarbershopSettings.DoesNotExist:
                pass

        # 2. Fallback a Twilio global si Twilio está habilitado
        if not IntegrationService.is_twilio_enabled():
            raise Exception("WhatsApp no está habilitado (ni por QR de cliente ni por pasarela global)")

        system_settings = IntegrationService.get_system_settings()
        account_sid = system_settings.twilio_account_sid or os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = system_settings.twilio_auth_token or os.getenv('TWILIO_AUTH_TOKEN')
        from_number = system_settings.twilio_phone_number or os.getenv('TWILIO_PHONE_NUMBER')

        if not all([account_sid, auth_token, from_number]):
            raise Exception("Twilio no está completamente configurado")

        try:
            from twilio.rest import Client
            client = Client(account_sid, auth_token)
            resp = client.messages.create(
                body=message,
                from_=f'whatsapp:{from_number}',
                to=f'whatsapp:{phone}'
            )
            logger.info("WhatsApp sent to %s: sid=%s", phone, resp.sid)
            return resp.sid
        except Exception as e:
            logger.error("Error sending WhatsApp to %s: %s", phone, str(e))
            from apps.audit_api.views import AuditLogViewSet
            AuditLogViewSet.log_integration_error('Twilio', f"Error enviando WhatsApp: {str(e)}")
            raise Exception(f"Error enviando WhatsApp: {str(e)}")



    @staticmethod
    def send_email(to_email, subject, html_message, text_message=None):
        """
        Enviar email transaccional usando Resend SMTP, SMTP propio, o fallback a consola.

        Prioridad:
          1. RESEND_API_KEY  → Resend HTTP API
          2. EMAIL_HOST/USER/PASSWORD  → SMTP genérico (incluye Resend SMTP)
          3. DEBUG=True  → ConsoleEmailBackend (desarrollo)
          4. Sin configuración  → excepción
        """
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        system_settings = IntegrationService.get_system_settings()

        resend_api_key = os.getenv('RESEND_API_KEY', '')
        smtp_host = os.getenv('EMAIL_HOST') or system_settings.smtp_host
        smtp_port = int(os.getenv('EMAIL_PORT') or system_settings.smtp_port or 587)
        smtp_user = os.getenv('EMAIL_HOST_USER') or system_settings.smtp_username
        smtp_password = os.getenv('EMAIL_HOST_PASSWORD') or system_settings.smtp_password
        use_tls = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
        from_email = os.getenv('DEFAULT_FROM_EMAIL') or system_settings.from_email or os.getenv('SENDGRID_FROM_EMAIL', '')
        is_debug = getattr(django_settings, 'DEBUG', False)
        email_backend = getattr(django_settings, 'EMAIL_BACKEND', 'NOT SET')
        logger.info("[EMAIL][SEND] entry to=%s subj=%s debug=%s backend=%s", to_email, subject, is_debug, email_backend)
        logger.info("[EMAIL][SEND] env: DEFAULT_FROM_EMAIL=%s RESEND_API_KEY=%s EMAIL_HOST=%s EMAIL_HOST_USER=%s EMAIL_PORT=%s use_tls=%s",
                    from_email or 'NOT SET',
                    'PRESENT' if resend_api_key else 'NOT SET',
                    smtp_host or 'NOT SET',
                    smtp_user or 'NOT SET',
                    smtp_port,
                    use_tls)

        if 'locmem' in email_backend or 'console' in email_backend:
            from django.core.mail import send_mail
            send_mail(
                subject,
                text_message or html_message,
                from_email or 'noreply@auronsuite.com',
                [to_email],
                html_message=html_message,
                fail_silently=False
            )
            return True

        # --- 1. Resend HTTP API (siempre primero — HTTPS puerto 443, más confiable que SMTP) ---
        using_resend_smtp = smtp_host and 'resend.com' in smtp_host.lower()
        resend_api_key = resend_api_key or (smtp_password if using_resend_smtp else '')
        logger.info("[EMAIL][Path1] Resend API check: key_present=%s key_starts_re=%s from=%s",
                    bool(resend_api_key), bool(resend_api_key.startswith('re_')) if resend_api_key else False,
                    from_email or 'noreply@auronsuite.com')
        if resend_api_key:
            try:
                import urllib.request
                import urllib.error
                import json as _json
                payload = _json.dumps({
                    'from': from_email or 'noreply@auronsuite.com',
                    'to': [to_email],
                    'subject': subject,
                    'html': html_message,
                    **(({'text': text_message}) if text_message else {}),
                }).encode()
                logger.info("[EMAIL][Path1] POST https://api.resend.com/emails from=%s to=%s payload_len=%d",
                            from_email or 'noreply@auronsuite.com', to_email, len(payload))
                req = urllib.request.Request(
                    'https://api.resend.com/emails',
                    data=payload,
                    headers={
                        'Authorization': f'Bearer {resend_api_key}',
                        'Content-Type': 'application/json',
                        'User-Agent': 'AuronSuite/1.0',
                    },
                    method='POST',
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw = resp.read()
                    status = resp.status
                    result = _json.loads(raw)
                logger.info("[EMAIL][Path1] Resend API success HTTP=%s body=%s id=%s to=%s",
                            status, result, result.get('id'), to_email)
                return result.get('id')
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors='replace')
                logger.warning("[EMAIL][Path1] Resend API HTTP error status=%s detail=%s — falling through to SMTP", e.code, detail)
            except Exception as e:
                logger.warning("[EMAIL][Path1] Resend API error sending to=%s: %s — falling through to SMTP", to_email, str(e))
 
        # --- 2. SMTP (intenta primero STARTTLS puerto por defecto, luego SSL 465) ---
        logger.info("[EMAIL][Path2] SMTP check: host=%s port=%s user=%s has_pwd=%s tls=%s",
                    smtp_host or 'NOT SET', smtp_port, smtp_user or 'NOT SET', bool(smtp_password), use_tls)
        if smtp_host and smtp_user and smtp_password:
            _smtp_errors = []
            for _port, _use_tls in [(smtp_port, use_tls), (465, False)]:
                try:
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = subject
                    msg['From'] = from_email or smtp_user
                    msg['To'] = to_email

                    if text_message:
                        msg.attach(MIMEText(text_message, 'plain', 'utf-8'))
                    msg.attach(MIMEText(html_message, 'html', 'utf-8'))

                    if _use_tls:
                        server = smtplib.SMTP(smtp_host, _port, timeout=10)
                        server.set_debuglevel(1)
                        server.starttls()
                    else:
                        server = smtplib.SMTP_SSL(smtp_host, _port, timeout=10)
                        server.set_debuglevel(1)

                    server.login(smtp_user, smtp_password)
                    failed = server.sendmail(msg['From'], [to_email], msg.as_string())
                    logger.info("[EMAIL][Path2] SMTP sendmail failed_recipients=%s (empty=success) to=%s port=%d", failed, to_email, _port)
                    server.quit()
                    logger.info("[EMAIL][Path2] Email sent via SMTP to=%s from=%s port=%d", to_email, from_email or smtp_user, _port)
                    return True
                except Exception as _e:
                    _smtp_errors.append(f"port {_port}: {_e}")
                    logger.warning("[EMAIL][Path2] SMTP failed on port %d: %s — trying next", _port, str(_e))

            last_err = _smtp_errors[-1] if _smtp_errors else 'unknown'
            logger.error("[EMAIL][Path2] All SMTP ports failed: %s", '; '.join(_smtp_errors))
            raise Exception(f"Error enviando email via SMTP: {last_err}")

        # --- 3. Fallback consola en desarrollo ---
        if is_debug:
            logger.warning("[EMAIL][Path3] Console fallback (DEBUG=True) to=%s from=%s", to_email, from_email or smtp_user)
            logger.warning(
                "EMAIL NOT CONFIGURED — printing to console\n"
                "To: %s\nSubject: %s\n%s",
                to_email, subject, text_message or html_message
            )
            return True

        logger.error("[EMAIL][SEND] ALL PATHS EXHAUSTED to=%s from=%s", to_email, from_email or smtp_user)
        raise Exception(
            "Email no configurado. Define RESEND_API_KEY o EMAIL_HOST/EMAIL_HOST_USER/EMAIL_HOST_PASSWORD en el entorno."
        )

    @staticmethod
    def upload_to_s3(file, bucket, key):
        """Subir archivo a S3 si esta habilitado"""
        if not IntegrationService.is_aws_s3_enabled():
            raise Exception("AWS S3 no esta habilitado")

        logger.info("S3 upload requested bucket=%s key=%s", bucket, key)
        return f"https://{bucket}.s3.amazonaws.com/{key}"
