import logging
import threading
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

def _send_in_background(to_email, subject, html_message):
    """Envía el email en un thread separado para no bloquear Gunicorn."""
    try:
        from apps.settings_api.integration_service import IntegrationService
        IntegrationService.send_email(to_email, subject, html_message)
        logger.info("Background email sent to %s", to_email)
    except Exception as e:
        logger.error("Background email error to %s: %s", to_email, str(e))

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_async(self, subject, message, from_email, recipient_list, html_message=None):
    override = getattr(settings, 'DEV_EMAIL_OVERRIDE', '')
    if override:
        recipient_list = [override]

    to_email = recipient_list[0]
    body = html_message or message

    # Si Celery corre eager (sin worker real), ejecutar en thread para no bloquear Gunicorn
    always_eager = getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)
    if always_eager:
        t = threading.Thread(target=_send_in_background, args=(to_email, subject, body), daemon=True)
        t.start()
        return

    try:
        from apps.settings_api.integration_service import IntegrationService
        IntegrationService.send_email(to_email, subject, body)
    except Exception as e:
        logger.error("Error sending email to %s: %s", recipient_list, str(e))
        raise self.retry(exc=e)
