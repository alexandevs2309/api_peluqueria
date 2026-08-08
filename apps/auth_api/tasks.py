import logging
import threading
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

def _send_in_background(to_email, subject, html_message):
    """Envía el email en un thread separado para no bloquear Gunicorn."""
    logger.info("[EMAIL][TASK] _send_in_background entry to=%s subj=%s", to_email, subject)
    try:
        from apps.settings_api.integration_service import IntegrationService
        result = IntegrationService.send_email(to_email, subject, html_message)
        logger.info("[EMAIL][TASK] _send_in_background completed to=%s result=%s", to_email, result)
    except Exception as e:
        logger.error("[EMAIL][TASK] _send_in_background failed to=%s: %s", to_email, str(e), exc_info=True)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_async(self, subject, message, from_email, recipient_list, html_message=None):
    logger.info("[EMAIL][TASK] send_email_async entry subj=%s from=%s to=%s", subject, from_email, recipient_list)
    override = getattr(settings, 'DEV_EMAIL_OVERRIDE', '')
    if override:
        recipient_list = [override]
        logger.info("[EMAIL][TASK] DEV_EMAIL_OVERRIDE active -> %s", override)

    to_email = recipient_list[0]
    body = html_message or message

    always_eager = getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)
    email_backend = getattr(settings, 'EMAIL_BACKEND', 'NOT SET')
    logger.info("[EMAIL][TASK] mode=%s backend=%s", "always_eager" if always_eager else "celery", email_backend)

    # Si Celery corre eager (sin worker real), ejecutar en thread para no bloquear Gunicorn
    if always_eager:
        t = threading.Thread(target=_send_in_background, args=(to_email, subject, body), daemon=True)
        t.start()
        return

    try:
        from apps.settings_api.integration_service import IntegrationService
        result = IntegrationService.send_email(to_email, subject, body)
        logger.info("[EMAIL][TASK] send_email completed to=%s result=%s", to_email, result)
    except Exception as e:
        logger.error("[EMAIL][TASK] send_email failed to=%s: %s", recipient_list, str(e), exc_info=True)
        raise self.retry(exc=e)
