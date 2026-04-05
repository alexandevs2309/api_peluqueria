from apps.settings_api.models import SystemSettings


def _get_system_settings():
    try:
        return SystemSettings.get_settings()
    except Exception:
        return None


def get_password_min_length(default: int = 8) -> int:
    settings = _get_system_settings()
    if settings is None:
        return default

    value = getattr(settings, 'password_min_length', default)
    try:
        return max(int(value), 1)
    except Exception:
        return default


def is_email_verification_required(default: bool = True) -> bool:
    settings = _get_system_settings()
    if settings is None:
        return default

    return bool(getattr(settings, 'require_email_verification', default))


def is_mfa_globally_enabled(default: bool = False) -> bool:
    settings = _get_system_settings()
    if settings is None:
        return default

    return bool(getattr(settings, 'enable_mfa', default))


def get_jwt_expiry_minutes(default: int = 60) -> int:
    settings = _get_system_settings()
    if settings is None:
        return default

    value = getattr(settings, 'jwt_expiry_minutes', default)
    try:
        return max(int(value), 5)
    except Exception:
        return default


def get_max_login_attempts(default: int = 5) -> int:
    settings = _get_system_settings()
    if settings is None:
        return default

    value = getattr(settings, 'max_login_attempts', default)
    try:
        return max(int(value), 1)
    except Exception:
        return default


def get_login_lockout_minutes(default: int = 5) -> int:
    settings = _get_system_settings()
    if settings is None:
        return default

    value = getattr(settings, 'login_lockout_minutes', default)
    try:
        return max(int(value), 1)
    except Exception:
        return default
