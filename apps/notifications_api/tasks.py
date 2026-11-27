from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from apps.core.rls_internal import internal_task
import logging

logger = logging.getLogger(__name__)

NO_SHOW_BATCH_SIZE = 500
MAX_NO_SHOW_BATCHES = 200

@shared_task(bind=True, max_retries=3, default_retry_delay=60, retry_backoff=True, retry_backoff_max=3600, retry_jitter=True)
@internal_task
def mark_expired_appointments(self):
    """Mark appointments as no_show if they passed and are still scheduled"""
    try:
        from apps.appointments_api.models import Appointment
        from apps.notifications_api.models import InAppNotification
        
        now = timezone.now()
        grace_minutes = getattr(settings, 'APPOINTMENT_NO_SHOW_GRACE_MINUTES', 15)
        cutoff_time = now - timedelta(minutes=grace_minutes)

        updated_count = 0
        notified_count = 0
        last_id = 0
        # Procesar por lotes acotados para no materializar todas las citas vencidas
        # en memoria ni construir un IN con miles de IDs. Un máximo de lotes evita
        # que un worker quede atrapado indefinidamente; la siguiente ejecución
        # continúa porque el filtro usa id__gt.
        for _ in range(MAX_NO_SHOW_BATCHES):
            batch = list(
                Appointment.objects.filter(
                    id__gt=last_id,
                    date_time__lt=cutoff_time,
                    status='scheduled',
                ).select_related('stylist', 'client').order_by('id')[:NO_SHOW_BATCH_SIZE]
            )
            if not batch:
                break

            appointment_ids = [appointment.id for appointment in batch]
            last_id = appointment_ids[-1]
            updated_count += Appointment.objects.filter(
                id__in=appointment_ids,
                status='scheduled',
            ).update(status='no_show')

            for appointment in batch:
                client_name = appointment.client.full_name if appointment.client else 'Cliente'
                dt_label = appointment.date_time.strftime('%d/%m/%Y %H:%M') if appointment.date_time else ''
                recipients = []
                if appointment.stylist_id:
                    recipients.append((appointment.stylist_id, f"El cliente {client_name} no asistió a la cita del {dt_label}"))
                client_user = getattr(appointment.client, 'user', None) if appointment.client else None
                if client_user and getattr(client_user, 'id', None):
                    recipients.append((client_user.id, f"Tu cita del {dt_label} fue marcada como no asistida."))
                try:
                    tenant_id = getattr(appointment, 'tenant_id', None)
                    if tenant_id:
                        from apps.auth_api.models import User
                        for uid in User.objects.filter(
                            tenant_id=tenant_id, roles__name='Client-Admin', is_active=True
                        ).distinct().values_list('id', flat=True):
                            recipients.append((uid, f"Cita marcada como no asistida: {client_name} · {dt_label}"))
                except Exception:
                    pass
                seen = set()
                for rid, msg in recipients:
                    if rid in seen:
                        continue
                    seen.add(rid)
                    InAppNotification.objects.create(
                        recipient_id=rid,
                        tenant_id=getattr(appointment, 'tenant_id', None),
                        type='appointment',
                        title='Cliente no asistió',
                        message=msg,
                    )
                    notified_count += 1

        logger.info(
            "Marked expired appointments as no_show updated=%s notifications=%s grace_minutes=%s",
            updated_count,
            notified_count,
            grace_minutes,
        )
        return f"Marked {updated_count} appointments as no_show"
    except Exception as e:
        logger.error(f"Error marking expired appointments: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, retry_backoff=True, retry_backoff_max=3600, retry_jitter=True)
@internal_task
def send_daily_appointment_reminders(self):
    """Send reminders for appointments scheduled for today"""
    try:
        from apps.appointments_api.models import Appointment
        from apps.notifications_api.models import InAppNotification
        
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        
        appointments = Appointment.objects.filter(
            date_time__date=today,
            status='scheduled'
        ).select_related('stylist', 'client', 'service')

        count = 0
        for appointment in appointments:
            if not appointment.stylist_id:
                continue
            client_name = appointment.client.full_name if appointment.client else 'Cliente'
            service_name = appointment.service.name if getattr(appointment, 'service', None) else 'Servicio'
            time_label = appointment.date_time.strftime('%H:%M') if appointment.date_time else ''
            # Evitar duplicados si la tarea se ejecuta más de una vez el mismo día
            if InAppNotification.objects.filter(
                recipient_id=appointment.stylist_id,
                type='appointment',
                title='Recordatorio: Cita hoy',
                message__contains=f"{client_name} a las {time_label}",
                created_at__date=today,
            ).exists():
                continue
            InAppNotification.objects.create(
                recipient_id=appointment.stylist_id,
                tenant_id=appointment.tenant_id,
                type='appointment',
                title='Recordatorio: Cita hoy',
                message=f"Cita con {client_name} a las {time_label}"
            )
            client_user = getattr(appointment.client, 'user', None) if appointment.client else None
            if client_user and getattr(client_user, 'id', None):
                if not InAppNotification.objects.filter(
                    recipient_id=client_user.id,
                    type='appointment',
                    title='Recordatorio: Tienes una cita hoy',
                    message__contains=time_label,
                    created_at__date=today,
                ).exists():
                    InAppNotification.objects.create(
                        recipient_id=client_user.id,
                        tenant_id=appointment.tenant_id,
                        type='appointment',
                        title='Recordatorio: Tienes una cita hoy',
                        message=f"Tu cita de {service_name} es hoy a las {time_label}."
                    )
            count += 1

        return f"Sent {count} daily reminders"
    except Exception as e:
        logger.error(f"Error sending daily reminders: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, retry_backoff=True, retry_backoff_max=3600, retry_jitter=True)
@internal_task
def notify_upcoming_appointments(self):
    """Notify about appointments starting in 1 hour"""
    try:
        from apps.appointments_api.models import Appointment
        from apps.notifications_api.models import InAppNotification
        
        now = timezone.now()
        one_hour_later = now + timedelta(hours=1)
        
        upcoming = Appointment.objects.filter(
            date_time__gte=now,
            date_time__lte=one_hour_later,
            status='scheduled'
        ).select_related('stylist', 'client', 'service')

        count = 0
        for appointment in upcoming:
            client_name = appointment.client.full_name if appointment.client else 'Cliente'
            service_name = appointment.service.name if getattr(appointment, 'service', None) else 'Servicio'
            time_label = appointment.date_time.strftime('%H:%M') if appointment.date_time else ''
            window_start = now - timedelta(minutes=70)
            if appointment.stylist_id and not InAppNotification.objects.filter(
                recipient_id=appointment.stylist_id,
                type='appointment',
                title='⏰ Cita próxima',
                message__contains=f"{client_name}",
                created_at__gte=window_start,
            ).exists():
                InAppNotification.objects.create(
                    recipient_id=appointment.stylist_id,
                    tenant_id=appointment.tenant_id,
                    type='appointment',
                    title='⏰ Cita próxima',
                    message=f"Cita con {client_name} en 1 hora ({time_label})"
                )
                count += 1
            client_user = getattr(appointment.client, 'user', None) if appointment.client else None
            if client_user and getattr(client_user, 'id', None) and not InAppNotification.objects.filter(
                recipient_id=client_user.id,
                type='appointment',
                title='⏰ Tu cita es pronto',
                message__contains=time_label,
                created_at__gte=window_start,
            ).exists():
                InAppNotification.objects.create(
                    recipient_id=client_user.id,
                    tenant_id=appointment.tenant_id,
                    type='appointment',
                    title='⏰ Tu cita es pronto',
                    message=f"Tu cita de {service_name} es en aproximadamente 1 hora ({time_label})."
                )

        return f"Notified {count} upcoming appointments"
    except Exception as e:
        logger.error(f"Error notifying upcoming appointments: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, retry_backoff=True, retry_backoff_max=3600)
@internal_task
def send_sms(self, phone, message):
    """Send SMS asynchronously via Twilio"""
    try:
        from apps.settings_api.integration_service import IntegrationService
        IntegrationService.send_sms(phone=phone, message=message)
    except Exception as e:
        logger.error("Error sending SMS to %s: %s", phone, str(e))
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, retry_backoff=True, retry_backoff_max=3600)
@internal_task
def send_whatsapp(self, phone, message):
    """Send WhatsApp message asynchronously via Twilio"""
    try:
        from apps.settings_api.integration_service import IntegrationService
        IntegrationService.send_whatsapp(phone=phone, message=message)
    except Exception as e:
        logger.error("Error sending WhatsApp to %s: %s", phone, str(e))
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=60, retry_backoff=True)
@internal_task
def send_appointment_reminders(self):
    """Send SMS and email reminders for tomorrow's appointments"""
    try:
        from apps.appointments_api.models import Appointment
        from apps.notifications_api.models import NotificationTemplate
        from apps.notifications_api.signals import NotificationService
        from django.db.models import Q

        tomorrow = timezone.now().date() + timedelta(days=1)
        appointments = Appointment.objects.filter(
            date_time__date=tomorrow,
            status='scheduled'
        ).select_related('client', 'stylist', 'service')

        service = NotificationService()
        sms_count = 0
        email_count = 0
        wa_count = 0

        for appointment in appointments:
            # SMS recordatorio
            if appointment.client and appointment.client.phone:
                phone = appointment.client.phone
                if not phone.startswith('+'):
                    phone = f'+1{phone}' if phone.isdigit() else phone
                send_sms.delay(
                    phone=phone,
                    message=f"Recordatorio: Tu cita en la barbería es mañana {appointment.date_time.strftime('%d/%m/%Y')} a las {appointment.date_time.strftime('%H:%M')}. Te esperamos!"
                )
                sms_count += 1

            # Email recordatorio
            tenant = getattr(appointment.stylist, 'tenant', None) if appointment.stylist else None
            try:
                template = NotificationTemplate.objects.get(
                    Q(notification_type='appointment_reminder'),
                    Q(type='email'),
                    Q(tenant=tenant) | Q(tenant__isnull=True),
                    is_active=True
                )
            except NotificationTemplate.DoesNotExist:
                continue

            context = {
                'client_name': appointment.client.full_name,
                'appointment_date': appointment.date_time.strftime('%d/%m/%Y'),
                'appointment_time': appointment.date_time.strftime('%H:%M'),
                'stylist_name': appointment.stylist.full_name if appointment.stylist else 'Por asignar',
                'service_name': appointment.service.name if appointment.service else 'Por definir'
            }

            service.create_notification(
                recipient=appointment.client.user if hasattr(appointment.client, 'user') else None,
                template=template,
                context_data=context,
                scheduled_at=timezone.now() + timedelta(hours=1)
            )
            email_count += 1

            # WhatsApp recordatorio
            try:
                wa_template = NotificationTemplate.objects.get(
                    Q(notification_type='appointment_reminder'),
                    Q(type='whatsapp'),
                    Q(tenant=tenant) | Q(tenant__isnull=True),
                    is_active=True
                )
                wa_recipient = appointment.client.user if hasattr(appointment.client, 'user') else None
                if wa_recipient:
                    service.create_notification(
                        recipient=wa_recipient,
                        template=wa_template,
                        context_data=context,
                        scheduled_at=timezone.now() + timedelta(hours=1)
                    )
                    wa_count += 1
            except NotificationTemplate.DoesNotExist:
                pass

        logger.info(
            "Sent appointment reminders for tomorrow: sms=%s emails=%s whatsapp=%s",
            sms_count,
            email_count,
            wa_count,
        )
        return f"Sent {sms_count} SMS, {email_count} email, and {wa_count} WhatsApp reminders for tomorrow"
    except Exception as e:
        logger.error(f"Error sending appointment reminders: {str(e)}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
@internal_task
def cleanup_old_notifications(self):
    """Delete read notifications older than 30 days"""
    try:
        from apps.notifications_api.models import InAppNotification
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        deleted_count, _ = InAppNotification.objects.filter(
            is_read=True,
            created_at__lt=thirty_days_ago
        ).delete()
        
        return f"Deleted {deleted_count} old notifications"
    except Exception as e:
        logger.error(f"Error cleaning up notifications: {str(e)}")
        raise self.retry(exc=e)
