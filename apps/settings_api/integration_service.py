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
        """Verificar si Email esta habilitado y configurado correctamente (sin conexión SMTP real)"""
        system_settings = IntegrationService.get_system_settings()
        has_env_smtp = bool(os.getenv('EMAIL_HOST') and os.getenv('EMAIL_HOST_USER') and os.getenv('EMAIL_HOST_PASSWORD'))
        if not system_settings.sendgrid_enabled and not has_env_smtp:
            return False

        smtp_host = IntegrationService._setting_or_env(system_settings.smtp_host, 'EMAIL_HOST', 'EMAIL_HOST')
        smtp_port = system_settings.smtp_port or int(os.getenv('EMAIL_PORT') or getattr(django_settings, 'EMAIL_PORT', 0) or 0)
        smtp_username = IntegrationService._setting_or_env(system_settings.smtp_username, 'EMAIL_HOST_USER', 'EMAIL_HOST_USER')
        smtp_password = IntegrationService._setting_or_env(system_settings.smtp_password, 'EMAIL_HOST_PASSWORD', 'EMAIL_HOST_PASSWORD')
        from_email = IntegrationService._setting_or_env(system_settings.from_email, 'DEFAULT_FROM_EMAIL', 'DEFAULT_FROM_EMAIL')

        api_key = os.getenv('SENDGRID_API_KEY')
        using_smtp = bool(smtp_host and smtp_port and smtp_username and smtp_password and from_email)

        if not using_smtp and not api_key:
            return False

        if api_key and not api_key.startswith('SG.'):
            return False
        return True

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
            'sendgrid': IntegrationService.is_sendgrid_enabled(),
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
    def send_email(to_email, subject, message, attachments=None):
        """Enviar email si email/SMTP esta habilitado"""
        if not IntegrationService.is_sendgrid_enabled():
            raise Exception("Email no configurado")

        try:
            from django.core.mail import EmailMessage, get_connection
            system_settings = IntegrationService.get_system_settings()

            smtp_host = IntegrationService._setting_or_env(system_settings.smtp_host, 'EMAIL_HOST', 'EMAIL_HOST')
            smtp_port = system_settings.smtp_port or int(os.getenv('EMAIL_PORT') or getattr(django_settings, 'EMAIL_PORT', 0) or 0)
            smtp_username = IntegrationService._setting_or_env(system_settings.smtp_username, 'EMAIL_HOST_USER', 'EMAIL_HOST_USER')
            smtp_password = IntegrationService._setting_or_env(system_settings.smtp_password, 'EMAIL_HOST_PASSWORD', 'EMAIL_HOST_PASSWORD')
            from_email = (
                IntegrationService._setting_or_env(system_settings.from_email, 'DEFAULT_FROM_EMAIL', 'DEFAULT_FROM_EMAIL')
                or django_settings.DEFAULT_FROM_EMAIL
            )
            from_name = system_settings.from_name

            use_ssl = smtp_port == 465
            use_tls = smtp_port in (587, 25) and not use_ssl

            from_header = from_email
            if from_name and from_email:
                from_header = f"{from_name} <{from_email}>"

            connection = None
            if smtp_host and smtp_port and smtp_username and smtp_password:
                connection = get_connection(
                    host=smtp_host,
                    port=smtp_port,
                    username=smtp_username,
                    password=smtp_password,
                    use_tls=use_tls,
                    use_ssl=use_ssl,
                    timeout=10,
                )

            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=from_header,
                to=[to_email],
                connection=connection,
            )
            email.content_subtype = "html"

            if attachments:
                for filename, content, mimetype in attachments:
                    email.attach(filename, content, mimetype)

            email.send(fail_silently=False)
            return True

        except Exception as e:
            from apps.audit_api.views import AuditLogViewSet
            AuditLogViewSet.log_integration_error('SendGrid', f"Error enviando email: {str(e)}")
            raise Exception(f"Error enviando email: {str(e)}")

    @staticmethod
    def upload_to_s3(file, bucket, key):
        """Subir archivo a S3 si esta habilitado"""
        if not IntegrationService.is_aws_s3_enabled():
            raise Exception("AWS S3 no esta habilitado")

        logger.info("S3 upload requested bucket=%s key=%s", bucket, key)
        return f"https://{bucket}.s3.amazonaws.com/{key}"
