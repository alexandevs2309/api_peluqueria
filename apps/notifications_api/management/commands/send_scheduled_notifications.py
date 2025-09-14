from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.notifications_api.models import Notification

class Command(BaseCommand):
    help = 'Enviar notificaciones programadas pendientes'

    def handle(self, *args, **options):
        now = timezone.now()
        pending_notifications = Notification.objects.filter(
            status='pending',
            scheduled_at__lte=now
        )
        total = pending_notifications.count()
        self.stdout.write(f'Enviando {total} notificaciones programadas...')

        sent_count = 0
        for notification in pending_notifications:
            success = notification.send()
            if success:
                sent_count += 1
                self.stdout.write(f'Notificación {notification.id} enviada a {notification.recipient.email}')
            else:
                self.stdout.write(f'Error enviando notificación {notification.id} a {notification.recipient.email}')

        self.stdout.write(self.style.SUCCESS(f'Proceso completado. {sent_count} notificaciones enviadas.'))
