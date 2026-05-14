import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_async(self, subject, message, from_email, recipient_list, html_message=None):
    override = getattr(settings, 'DEV_EMAIL_OVERRIDE', '')
    if override:
        recipient_list = [override]
    try:
        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        logger.error("Error sending email to %s: %s", recipient_list, str(e))
        raise self.retry(exc=e)
