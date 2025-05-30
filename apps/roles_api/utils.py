from .models import AdminActionLog
from django.http import HttpRequest

def log_admin_action(request, action):
    AdminActionLog.objects.create(
        user=request.user,
        action=action,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )

def get_client_ip(request: HttpRequest):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')
