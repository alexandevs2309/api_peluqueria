export function roleKey(role: string | null | undefined): string {
    const raw = (role || '').trim();
    if (!raw) return '';

    return raw
        .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
        .toUpperCase()
        .replace(/[\s-]+/g, '_');
}

const LEGACY_ROLE_LABELS: Record<string, string> = {
    SUPER_ADMIN: 'Super Admin',
    CLIENT_ADMIN: 'Dueño',
    MANAGER: 'Gerente',
    CAJERA: 'Cajera',
    ESTILISTA: 'Estilista',
    CLIENT_STAFF: 'Staff',
    UTILITY: 'Utilidad',
};

const BUSINESS_ROLE_LABELS: Record<string, string> = {
    owner: 'Propietario',
    manager: 'Gerente',
    frontdesk_cashier: 'Recepcion / Caja',
    professional: 'Profesional',
};

const LEGACY_TO_BUSINESS_ROLE: Record<string, string> = {
    SUPER_ADMIN: 'internal_support',
    SUPERADMIN: 'internal_support',
    CLIENT_ADMIN: 'owner',
    CLIENTADMIN: 'owner',
    MANAGER: 'manager',
    CAJERA: 'frontdesk_cashier',
    ESTILISTA: 'professional',
    CLIENT_STAFF: 'professional',
    CLIENTSTAFF: 'professional',
    UTILITY: 'internal_support',
};

const NORMALIZE_ROLE_MAP: Record<string, string> = {
    SUPERADMIN: 'SUPER_ADMIN',
    SUPER_ADMIN: 'SUPER_ADMIN',
    CLIENTADMIN: 'CLIENT_ADMIN',
    CLIENT_ADMIN: 'CLIENT_ADMIN',
    CLIENT_ADMINISTRATOR: 'CLIENT_ADMIN',
    UTILITY: 'UTILITY',
    CLIENTSTAFF: 'CLIENT_STAFF',
    CLIENT_STAFF: 'CLIENT_STAFF',
    MANAGER: 'MANAGER',
    CAJERA: 'CAJERA',
    ESTILISTA: 'ESTILISTA',
    // ⚠️ MIGRACIÓN RBAC: business roles mapeados a su legacy equivalente
    OWNER: 'CLIENT_ADMIN',
    FRONTDESK_CASHIER: 'CAJERA',
    PROFESSIONAL: 'ESTILISTA',
    INTERNAL_SUPPORT: 'UTILITY',
};

export function normalizeRole(role: string | null | undefined): string {
    const normalizedInput = String(role || '').trim().toUpperCase();
    const key = roleKey(normalizedInput);
    return NORMALIZE_ROLE_MAP[key] || 'UNKNOWN';
}

export function normalizeBusinessRole(role: string | null | undefined): string {
    const raw = (role || '').trim();
    if (!raw) return '';

    return raw
        .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
        .toLowerCase()
        .replace(/[\s-]+/g, '_');
}

export function resolveBusinessRole(role: string | null | undefined, businessRole?: string | null): string {
    const explicitBusinessRole = normalizeBusinessRole(businessRole);
    if (explicitBusinessRole) {
        return explicitBusinessRole;
    }

    const legacyRoleKey = normalizeRole(role);
    return LEGACY_TO_BUSINESS_ROLE[legacyRoleKey] || '';
}

export function getRoleDisplayLabel(
    role: string | null | undefined,
    businessRole?: string | null,
    _businessRoleDisplay?: string | null
): string {
    const bRole = resolveBusinessRole(role, businessRole);
    if (bRole && bRole in BUSINESS_ROLE_LABELS) {
        return BUSINESS_ROLE_LABELS[bRole];
    }

    const normalizedRole = normalizeRole(role);
    return LEGACY_ROLE_LABELS[normalizedRole] || (normalizedRole === 'UNKNOWN' ? 'Sin rol' : normalizedRole);
}

export function isServiceAssignableRole(role: string | null | undefined, businessRole?: string | null): boolean {
    return resolveBusinessRole(role, businessRole) === 'professional';
}
