import logging
from django.conf import settings
from django.template import Template, Context
from django.utils import timezone
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
        Enviar notificación por email
        """
        try:
            # Aquí iría la integración con SendGrid, Mailgun, etc.
            # Por ahora, simulamos el envío

            # En un entorno real, usarías:
            # from sendgrid import SendGridAPIClient
            # from sendgrid.helpers.mail import Mail

            logger.info(f"Email would be sent to {notification.recipient.email}: {notification.subject}")

            # Crear log
            NotificationLog.objects.create(
                notification=notification,
                channel='email',
                provider='sendgrid',  # o el que uses
                status='sent',
                response_data={'simulated': True}
            )

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
            logger.info(f"SMS would be sent to {notification.recipient.username}: {notification.message[:50]}...")

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

    def _send_push(self, notification):
        """
        Enviar notificación push
        """
        try:
            # Integración con Firebase Cloud Messaging
            logger.info(f"Push notification would be sent to {notification.recipient.username}")

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
            sent=Count('id', filter=models.Q(status='sent')),
            failed=Count('id', filter=models.Q(status='failed')),
            pending=Count('id', filter=models.Q(status='pending')),
        )
