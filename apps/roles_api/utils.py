from .models import AdminActionLog
from django.http import HttpRequest

def log_admin_action(request: HttpRequest, action: str):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return  # No log para usuario anónimo

    AdminActionLog.objects.create(
        user=user,
        action=action,
        ip_address=get_client_ip(request) or 'unknown',
        user_agent=request.META.get('HTTP_USER_AGENT', 'unknown')
    )

def get_client_ip(request: HttpRequest):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
