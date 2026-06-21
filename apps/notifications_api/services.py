import logging
from django.conf import settings
from django.template import Template, Context
from django.utils import timezone
from django.db.models import Q
from .models import Notification, NotificationLog, NotificationPreference

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Servicio para manejar el envío de notificaciones
    """

    def create_notification(self, recipient, template, context_data=None, scheduled_at=None, priority='normal'):
        """
        Crear una notificación a partir de un template
        """
        context_data = context_data or {}

        # Renderizar template
        subject = self._render_template(template.subject or '', context_data)
        message = self._render_template(template.body, context_data)

        # Crear notificación
        notification = Notification.objects.create(
            recipient=recipient,
            template=template,
            subject=subject,
            message=message,
            scheduled_at=scheduled_at,
            priority=priority,
            metadata=context_data
        )

        logger.info(f"Notification created: {notification.id} for {recipient.email}")

        # Si no está programada, enviarla inmediatamente
        if not scheduled_at:
            self.send_notification(notification)

        return notification

    def send_notification(self, notification):
        """
        Enviar una notificación específica
        """
        try:
            # Verificar preferencias del usuario
            preferences = self._get_user_preferences(notification.recipient)

            # Enviar por los canales habilitados
            success = False

            if preferences.email_enabled and notification.template.type == 'email':
                if self._send_email(notification):
                    success = True

            if preferences.sms_enabled and notification.template.type == 'sms':
                if self._send_sms(notification):
                    success = True

            if preferences.push_enabled and notification.template.type == 'push':
                if self._send_push(notification):
                    success = True

            if preferences.whatsapp_enabled and notification.template.type == 'whatsapp':
                if self._send_whatsapp(notification):
                    success = True

            if success:
                notification.status = 'sent'
                notification.sent_at = timezone.now()
            else:
                notification.status = 'failed'
                notification.error_message = 'No se pudo enviar por ningún canal'

            notification.save()
            return success

        except Exception as e:
            logger.error(f"Error sending notification {notification.id}: {str(e)}")
            notification.status = 'failed'
            notification.error_message = str(e)
            notification.save()
            return False

    def _send_email(self, notification):
        """
        Enviar notificación por email usando IntegrationService
        """
        try:
            from apps.settings_api.integration_service import IntegrationService

            recipient = notification.recipient.email
            if not recipient:
                logger.warning("Cannot send email notification: recipient has no email")
                return False

            attachments = []
            if notification.template.notification_type == 'appointment_confirmation':
                from apps.appointments_api.models import Appointment
                try:
                    appointment_id = notification.metadata.get('appointment_id')
                    if appointment_id:
                        appointment = Appointment.objects.get(id=int(appointment_id))
                        ics_content = self.generate_ics_content(
                            appointment,
                            stylist_name=notification.metadata.get('stylist_name', 'Por asignar'),
                            service_name=notification.metadata.get('service_name', 'Por definir'),
                            client_name=notification.metadata.get('client_name', 'Cliente')
                        )
                        attachments.append(('invitacion.ics', ics_content, 'text/calendar'))
                except Exception as e:
                    logger.warning("Failed to generate ICS attachment: %s", str(e))

            IntegrationService.send_email(
                to_email=recipient,
                subject=notification.subject,
                message=notification.message,
                attachments=attachments,
            )

            NotificationLog.objects.create(
                notification=notification,
                channel='email',
                provider='sendgrid',
                status='sent',
                response_data={'sent_via': 'IntegrationService'}
            )

            logger.info(f"Email sent to {recipient}: {notification.subject}")
            return True

        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            NotificationLog.objects.create(
                notification=notification,
                channel='email',
                provider='sendgrid',
                status='failed',
                error_message=str(e)
            )
            return False

    def _send_sms(self, notification):
        """
        Enviar notificación por SMS
        """
        try:
            # Integración con Twilio u otro proveedor SMS
            logger.info(f"SMS would be sent to {notification.recipient.email}: {notification.message[:50]}...")

            NotificationLog.objects.create(
                notification=notification,
                channel='sms',
                provider='twilio',
                status='sent',
                response_data={'simulated': True}
            )

            return True

        except Exception as e:
            logger.error(f"SMS sending failed: {str(e)}")
            NotificationLog.objects.create(
                notification=notification,
                channel='sms',
                provider='twilio',
                status='failed',
                error_message=str(e)
            )
            return False

    def _send_whatsapp(self, notification):
        """
        Enviar notificación por WhatsApp usando la capa de abstracción.
        """
        try:
            from apps.notifications_api.provider import get_notification_provider
            # Determinar tenant asociado al destinatario (cliente)
            tenant = getattr(notification.recipient, 'tenant', None)
            if not tenant and notification.template and getattr(notification.template, 'tenant', None):
                tenant = notification.template.tenant
            if not tenant:
                logger.warning('WhatsApp send attempted without tenant context; skipping.')
                return False
            # Obtener provider para contexto de cliente
            provider = get_notification_provider(context='client', tenant=tenant)
            phone = getattr(notification.recipient, 'phone', None)
            if not phone or not str(phone).strip():
                logger.warning('Cannot send WhatsApp notification: recipient has no phone')
                return False
            # Normalizar número
            if not str(phone).startswith('+'):
                phone = f'+1{phone}' if str(phone).isdigit() else phone
            # Enviar vía Evolution
            provider.send_whatsapp(to=phone, template=notification.message, data={})
            NotificationLog.objects.create(
                notification=notification,
                channel='whatsapp',
                provider='evolution_api',
                status='sent',
                response_data={'phone': phone, 'method': 'evolution_api'}
            )
            return True
        except Exception as e:
            logger.error(f"WhatsApp sending failed via Evolution API: {str(e)}")
            NotificationLog.objects.create(
                notification=notification,
                channel='whatsapp',
                provider='unknown',
                status='failed',
                error_message=str(e)
            )
            return False

    def _send_push(self, notification):
        """
        Enviar notificación push
        """
        try:
            # Integración con Firebase Cloud Messaging
            logger.info(f"Push notification would be sent to {notification.recipient.email}")

            NotificationLog.objects.create(
                notification=notification,
                channel='push',
                provider='firebase',
                status='sent',
                response_data={'simulated': True}
            )

            return True

        except Exception as e:
            logger.error(f"Push sending failed: {str(e)}")
            NotificationLog.objects.create(
                notification=notification,
                channel='push',
                provider='firebase',
                status='failed',
                error_message=str(e)
            )
            return False

    def _render_template(self, template_text, context_data):
        """
        Renderizar template con variables
        """
        if not template_text:
            return ''

        template = Template(template_text)
        context = Context(context_data)
        return template.render(context)

    def _get_user_preferences(self, user):
        """
        Obtener preferencias de notificación del usuario
        """
        preferences, created = NotificationPreference.objects.get_or_create(
            user=user,
            defaults={
                'email_enabled': True,
                'sms_enabled': False,
                'push_enabled': True,
                'whatsapp_enabled': False,
                'appointment_reminders': True,
                'payment_notifications': True,
                'earnings_notifications': True,
                'system_notifications': True,
                'marketing_notifications': False,
            }
        )
        return preferences

    def send_bulk_notifications(self, notifications):
        """
        Enviar múltiples notificaciones
        """
        results = []
        for notification in notifications:
            result = self.send_notification(notification)
            results.append(result)
        return results

    def get_notification_stats(self, user=None, days=30):
        """
        Obtener estadísticas de notificaciones
        """
        from django.db.models import Count
        from datetime import timedelta

        queryset = Notification.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=days)
        )

        if user:
            queryset = queryset.filter(recipient=user)

        return queryset.aggregate(
            total=Count('id'),
            sent=Count('id', filter=Q(status='sent')),
            failed=Count('id', filter=Q(status='failed')),
            pending=Count('id', filter=Q(status='pending')),
        )

    def generate_ics_content(self, appointment, stylist_name, service_name, client_name):
        from datetime import timedelta, timezone as dt_timezone
        # Formatear fechas en formato iCalendar: YYYYMMDDTHHMMSSZ
        utc_dt = appointment.date_time.astimezone(dt_timezone.utc)
        dtstart = utc_dt.strftime('%Y%m%dT%H%M%SZ')
        
        # Calcular fin de la cita (duración)
        duration = appointment.service.duration if appointment.service else 30
        dtend = (utc_dt + timedelta(minutes=duration)).strftime('%Y%m%dT%H%M%SZ')
        dtstamp = timezone.now().astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        
        # Generar un UID único
        uid = f"appointment-{appointment.id}@{appointment.tenant_id or 'auronsuite'}.com"
        
        summary = f"Cita: {service_name} con {stylist_name}"
        description = f"Hola {client_name},\\n\\nTu cita para {service_name} con {stylist_name} ha sido confirmada.\\nFecha: {appointment.date_time.strftime('%d/%m/%Y a las %H:%M')}.\\n\\n¡Te esperamos!"
        
        # Construir el cuerpo del archivo ICS
        ics = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//AuronSuite//NONSGML Calendar//ES",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            "STATUS:CONFIRMED",
            "SEQUENCE:0",
            "TRANSP:OPAQUE",
            "END:VEVENT",
            "END:VCALENDAR"
        ]
        return "\r\n".join(ics)
