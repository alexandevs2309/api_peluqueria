from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_appointment_reminders():
    """Enviar recordatorios de citas para mañana"""
    try:
        from .signals import create_appointment_reminders
        create_appointment_reminders()
        logger.info("Recordatorios de citas enviados correctamente")
        return "Recordatorios enviados"
    except Exception as e:
        logger.error(f"Error enviando recordatorios: {str(e)}")
        return f"Error: {str(e)}"

@shared_task
def process_scheduled_notifications():
    """Procesar notificaciones programadas"""
    try:
        from .models import Notification
        from .services import NotificationService
        
        # Obtener notificaciones programadas para ahora
        now = timezone.now()
        scheduled_notifications = Notification.objects.filter(
            status='pending',
            scheduled_at__lte=now
        )
        
        service = NotificationService()
        sent_count = 0
        
        for notification in scheduled_notifications:
            if service.send_notification(notification):
                sent_count += 1
        
        logger.info(f"Procesadas {sent_count} notificaciones programadas")
        return f"Procesadas {sent_count} notificaciones"
        
    except Exception as e:
        logger.error(f"Error procesando notificaciones: {str(e)}")
        return f"Error: {str(e)}"

@shared_task
def cleanup_old_notifications():
    """Limpiar notificaciones antiguas"""
    try:
        from .models import Notification, NotificationLog
        
        # Eliminar notificaciones de más de 90 días
        cutoff_date = timezone.now() - timedelta(days=90)
        
        old_notifications = Notification.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['sent', 'failed']
        )
        
        count = old_notifications.count()
        old_notifications.delete()
        
        # Limpiar logs antiguos también
        old_logs = NotificationLog.objects.filter(
            created_at__lt=cutoff_date
        )
        log_count = old_logs.count()
        old_logs.delete()
        
        logger.info(f"Limpiadas {count} notificaciones y {log_count} logs antiguos")
        return f"Limpiadas {count} notificaciones y {log_count} logs"
        
    except Exception as e:
        logger.error(f"Error limpiando notificaciones: {str(e)}")
        return f"Error: {str(e)}"

@shared_task
def send_bulk_notifications(notification_ids):
    """Enviar múltiples notificaciones en lote"""
    try:
        from .models import Notification
        from .services import NotificationService
        
        notifications = Notification.objects.filter(
            id__in=notification_ids,
            status='pending'
        )
        
        service = NotificationService()
        results = service.send_bulk_notifications(notifications)
        
        sent_count = sum(1 for result in results if result)
        total_count = len(results)
        
        logger.info(f"Enviadas {sent_count}/{total_count} notificaciones en lote")
        return f"Enviadas {sent_count}/{total_count} notificaciones"
        
    except Exception as e:
        logger.error(f"Error enviando notificaciones en lote: {str(e)}")
        return f"Error: {str(e)}"