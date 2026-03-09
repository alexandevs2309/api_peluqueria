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

