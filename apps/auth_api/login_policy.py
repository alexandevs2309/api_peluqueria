from datetime import timedelta

from django.utils.timezone import now

from .models import LoginAudit
from .settings_policy import get_max_login_attempts, get_login_lockout_minutes


def is_login_locked_out(user=None, ip_address: str | None = None) -> bool:
    lockout_minutes = get_login_lockout_minutes()
    threshold = now() - timedelta(minutes=lockout_minutes)
    limit = get_max_login_attempts()

    if user is not None:
        failures = LoginAudit.objects.filter(
            user=user,
            successful=False,
            timestamp__gte=threshold,
        ).count()
        if failures >= limit:
            return True

    if ip_address:
        failures = LoginAudit.objects.filter(
            ip_address=ip_address,
            successful=False,
            timestamp__gte=threshold,
        ).count()
        if failures >= limit:
            return True

    return False


def get_login_lockout_message() -> str:
    lockout_minutes = get_login_lockout_minutes()
    return (
        f"Demasiados intentos fallidos. Intenta de nuevo en "
        f"{lockout_minutes} minutos."
    )
