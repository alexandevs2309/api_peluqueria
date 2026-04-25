import re


ROLE_ALIASES = {
    'SUPERADMIN': 'SUPER_ADMIN',
    'CLIENTADMIN': 'CLIENT_ADMIN',
    'CLIENTSTAFF': 'CLIENT_STAFF',
}


def normalize_role_for_api(role: str | None, is_superuser: bool = False) -> str:
    """Normalize role labels to API format (UPPER_SNAKE_CASE)."""
    raw = (role or '').strip()
    if not raw:
        return 'SUPER_ADMIN' if is_superuser else ''

    key = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', raw)
    key = re.sub(r'[\s-]+', '_', key).upper()
    return ROLE_ALIASES.get(key, key)


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
