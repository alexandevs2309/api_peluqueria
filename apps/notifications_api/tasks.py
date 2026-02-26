from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def mark_expired_appointments(self):
    """Mark appointments as no_show if they passed and are still scheduled"""
    try:
        from apps.appointments_api.models import Appointment
        from apps.notifications_api.models import InAppNotification
        
        now = timezone.now()
        expired_appointments = Appointment.objects.filter(
            date_time__lt=now,
            status='scheduled'
        ).select_related('stylist', 'client')
        
        count = 0
        for appointment in expired_appointments:
            appointment.status = 'no_show'
            appointment.save()
            
            # Create notification for stylist
            InAppNotification.objects.create(
                recipient=appointment.stylist,
                type='appointment',
                title='Cliente no asistió',
                message=f"El cliente {appointment.client.full_name} no asistió a la cita del {appointment.date_time.strftime('%d/%m/%Y %H:%M')}"
            )
            count += 1
        
        return f"Marked {count} appointments as no_show"
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
