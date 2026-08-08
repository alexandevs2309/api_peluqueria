import os
from django.core.management.base import BaseCommand
from apps.settings_api.models import SystemSettings


class Command(BaseCommand):
    help = 'Configura SMTP de Gmail para envio de correos'

    def handle(self, *args, **options):
        password = os.environ.get('GMAIL_APP_PASSWORD')
        if not password:
            self.stdout.write(self.style.WARNING(
                'GMAIL_APP_PASSWORD no definida. '
                'Usa: GMAIL_APP_PASSWORD=xxxx python manage.py setup_smtp'
            ))
            return

        settings = SystemSettings.get_settings()
        settings.smtp_host = 'smtp.gmail.com'
        settings.smtp_port = 587
        settings.smtp_username = 'teacheracardenas@gmail.com'
        settings.smtp_password = password
        settings.from_email = 'notificaciones@auronsuite.com'
        settings.from_name = 'Auron Suite'
        settings.sendgrid_enabled = True
        settings.save()
        self.stdout.write(self.style.SUCCESS('SMTP configurado exitosamente'))
