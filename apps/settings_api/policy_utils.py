from decimal import Decimal


DEFAULT_PLATFORM_COMMISSION_RATE = Decimal("5.00")


def _get_system_settings():
    try:
        from apps.settings_api.models import SystemSettings

        return SystemSettings.get_settings()
    except Exception:
        return None


def get_platform_commission_rate() -> Decimal:
    settings = _get_system_settings()
    if settings is None:
        return DEFAULT_PLATFORM_COMMISSION_RATE

    value = getattr(settings, "platform_commission_rate", DEFAULT_PLATFORM_COMMISSION_RATE)
    try:
        return Decimal(str(value))
    except Exception:
        return DEFAULT_PLATFORM_COMMISSION_RATE


def calculate_platform_commission(amount) -> Decimal:
    amount_decimal = Decimal(str(amount or 0))
    rate = get_platform_commission_rate()
    return (amount_decimal * rate) / Decimal("100")


def calculate_platform_net_revenue(amount) -> Decimal:
    amount_decimal = Decimal(str(amount or 0))
    return amount_decimal - calculate_platform_commission(amount_decimal)


def should_auto_suspend_expired() -> bool:
    settings = _get_system_settings()
    if settings is None:
        return True

    return bool(getattr(settings, "auto_suspend_expired", True))
