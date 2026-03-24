from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_email_async(subject, message, from_email, recipient_list, html_message=None):
    override = getattr(settings, 'DEV_EMAIL_OVERRIDE', '')
    if override:
        recipient_list = [override]
    send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        html_message=html_message,
        fail_silently=False,
    )
