from rest_framework_simplejwt.tokens import AccessToken
from django.utils import timezone


def _login_window_start(window_minutes: int = 15):
    return timezone.now() - timezone.timedelta(minutes=window_minutes)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def get_user_agent(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    # Truncar a 255 caracteres para evitar error DataError
    return user_agent[:255] if user_agent else ''

def get_client_jti(token:str):
    try:
        token = AccessToken(token)
        return token.get('jti')
    except Exception as e:
        return None


def resolve_login_user(email, tenant_subdomain=None):
    from django.contrib.auth import get_user_model
    from apps.tenants_api.models import Tenant

    User = get_user_model()
    normalized_email = (email or '').strip().lower()
    if not normalized_email:
        return None

    if tenant_subdomain:
        tenant = Tenant.objects.filter(subdomain=tenant_subdomain).first()
        if not tenant:
            return None
        return User.objects.filter(email=normalized_email, tenant=tenant).first()

    return User.objects.filter(email=normalized_email).first()


def exceeded_login_attempts(user, max_attempts: int, window_minutes: int = 15) -> bool:
    if not user or max_attempts <= 0:
        return False

    from .models import LoginAudit

    window_start = _login_window_start(window_minutes)
    last_success = LoginAudit.objects.filter(
        user=user,
        successful=True,
        timestamp__gte=window_start
    ).order_by('-timestamp').values_list('timestamp', flat=True).first()

    failed_attempts = LoginAudit.objects.filter(
        user=user,
        successful=False,
        timestamp__gte=last_success or window_start
    ).count()

    return failed_attempts >= max_attempts
