import re


ROLE_ALIASES = {
    'SUPERADMIN': 'SUPER_ADMIN',
    'CLIENTADMIN': 'CLIENT_ADMIN',
    'CLIENTSTAFF': 'CLIENT_STAFF',
}

LEGACY_TO_BUSINESS_ROLE = {
    'SuperAdmin': 'internal_support',
    'Soporte': 'internal_support',
    'Client-Admin': 'owner',
    'Manager': 'manager',
    'Cajera': 'frontdesk_cashier',
    'Estilista': 'professional',
    'Client-Staff': 'professional',
    'Utility': 'professional',
}

BUSINESS_ROLE_TO_LEGACY_ROLE = {
    'internal_support': 'SuperAdmin',
    'owner': 'Client-Admin',
    'manager': 'Manager',
    'frontdesk_cashier': 'Cajera',
    'professional': 'Estilista',
    'marketing': 'Client-Staff',
    'accounting': 'Manager',
}

BUSINESS_ROLE_DISPLAY = {
    'internal_support': 'Soporte interno',
    'owner': 'Propietario',
    'manager': 'Gerente',
    'frontdesk_cashier': 'Recepcion / Caja',
    'professional': 'Profesional',
    'marketing': 'Marketing',
    'accounting': 'Contabilidad',
}


def normalize_role_for_api(role: str | None, is_superuser: bool = False) -> str:
    """Normalize role labels to API format (UPPER_SNAKE_CASE)."""
    raw = (role or '').strip()
    if not raw:
        return 'SUPER_ADMIN' if is_superuser else ''

    key = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', raw)
    key = re.sub(r'[\s-]+', '_', key).upper()
    return ROLE_ALIASES.get(key, key)


def normalize_business_role(role: str | None, is_superuser: bool = False) -> str:
    raw = (role or '').strip()
    if not raw:
        return 'internal_support' if is_superuser else ''

    key = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', raw)
    key = re.sub(r'[\s-]+', '_', key).lower()
    return key


def map_legacy_role_to_business_role(role: str | None, is_superuser: bool = False) -> str:
    if is_superuser:
        return 'internal_support'
    return LEGACY_TO_BUSINESS_ROLE.get((role or '').strip(), '')


def map_business_role_to_legacy_role(role: str | None, is_superuser: bool = False) -> str:
    normalized = normalize_business_role(role, is_superuser=is_superuser)
    if normalized == 'internal_support' and is_superuser:
        return 'SuperAdmin'
    return BUSINESS_ROLE_TO_LEGACY_ROLE.get(normalized, '')


def get_business_role_display(role: str | None, is_superuser: bool = False) -> str:
    normalized = normalize_business_role(role, is_superuser=is_superuser)
    return BUSINESS_ROLE_DISPLAY.get(normalized, normalized.replace('_', ' ').title() if normalized else '')


def get_effective_role_name(user, tenant=None) -> str:
    """Resolve current role preferring UserRole over the legacy field."""
    if not user:
        return ''
    if getattr(user, 'is_superuser', False):
        return 'SuperAdmin'

    if tenant is None:
        tenant = getattr(user, 'tenant', None)

    try:
        from apps.roles_api.models import UserRole

        role_qs = UserRole.objects.filter(user=user)
        if tenant is not None:
            role_qs = role_qs.filter(tenant=tenant)

        role_name = role_qs.values_list('role__name', flat=True).first()
        if role_name:
            return role_name
    except Exception:
        pass

    return (getattr(user, 'role', None) or '').strip()


def get_effective_role_api(user, tenant=None) -> str:
    return normalize_role_for_api(
        get_effective_role_name(user, tenant=tenant),
        is_superuser=getattr(user, 'is_superuser', False)
    )


def get_effective_business_role(user, tenant=None) -> str:
    if not user:
        return ''

    if getattr(user, 'is_superuser', False):
        return 'internal_support'

    explicit_business_role = normalize_business_role(
        getattr(user, 'business_role', None),
        is_superuser=getattr(user, 'is_superuser', False)
    )
    if explicit_business_role:
        return explicit_business_role

    return map_legacy_role_to_business_role(
        get_effective_role_name(user, tenant=tenant),
        is_superuser=getattr(user, 'is_superuser', False)
    )


def get_effective_business_role_display(user, tenant=None) -> str:
    return get_business_role_display(
        get_effective_business_role(user, tenant=tenant),
        is_superuser=getattr(user, 'is_superuser', False)
    )
