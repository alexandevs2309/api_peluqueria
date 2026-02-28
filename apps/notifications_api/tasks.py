from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def mark_expired_appointments(self):
    """Mark appointments as no_show if they passed and are still scheduled"""
    try:
        from apps.appointments_api.models import Appointment
        from apps.notifications_api.models import InAppNotification
        
        now = timezone.now()
        grace_minutes = getattr(settings, 'APPOINTMENT_NO_SHOW_GRACE_MINUTES', 15)
        cutoff_time = now - timedelta(minutes=grace_minutes)

        expired_appointments = Appointment.objects.filter(
            date_time__lt=cutoff_time,
            status='scheduled'
        ).select_related('stylist', 'client')
        
        if not expired_appointments.exists():
            logger.info("No expired appointments to mark as no_show")
            return "Marked 0 appointments as no_show"

        # Snapshot for notifications before bulk update.
        expired_data = list(expired_appointments)
        appointment_ids = [appt.id for appt in expired_data]

        updated_count = Appointment.objects.filter(
            id__in=appointment_ids,
            status='scheduled'
        ).update(status='no_show')

        count = 0
        for appointment in expired_data:
            # Create notification for stylist
            InAppNotification.objects.create(
                recipient=appointment.stylist,
                type='appointment',
                title='Cliente no asistió',
                message=f"El cliente {appointment.client.full_name} no asistió a la cita del {appointment.date_time.strftime('%d/%m/%Y %H:%M')}"
            )
            count += 1
        
        logger.info(
            "Marked expired appointments as no_show updated=%s notifications=%s grace_minutes=%s",
            updated_count,
            count,
            grace_minutes,
        )
        return f"Marked {updated_count} appointments as no_show"
    except Exception as e:
        logger.error(f"Error marking expired appointments: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
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
            # Notification for stylist
            InAppNotification.objects.create(
                recipient=appointment.stylist,
                type='appointment',
                title='Recordatorio: Cita hoy',
                message=f"Cita con {appointment.client.full_name} a las {appointment.date_time.strftime('%H:%M')}"
            )
            count += 1
        
        return f"Sent {count} daily reminders"
    except Exception as e:
        logger.error(f"Error sending daily reminders: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
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
        ).select_related('stylist', 'client')
        
        count = 0
        for appointment in upcoming:
            InAppNotification.objects.create(
                recipient=appointment.stylist,
                type='appointment',
                title='⏰ Cita próxima',
                message=f"Cita con {appointment.client.full_name} en 1 hora ({appointment.date_time.strftime('%H:%M')})"
            )
            count += 1
        
        return f"Notified {count} upcoming appointments"
    except Exception as e:
        logger.error(f"Error notifying upcoming appointments: {str(e)}")
        raise self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
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
