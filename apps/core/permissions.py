"""
Permisos centralizados para el sistema multi-tenant.
Evita duplicación de permisos comunes en múltiples apps.
"""
from rest_framework.permissions import BasePermission
from apps.roles_api.models import UserRole
from apps.auth_api.role_utils import get_effective_role_name


def _resolve_permission_tenant(request):
    tenant = getattr(request, 'tenant', None)
    if tenant is not None:
        return tenant

    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False):
        return getattr(user, 'tenant', None)

    return None


def _matches_role(role_name, *candidates):
    aliases = {
        'Admin': 'Client-Admin',
        'Stylist': 'Estilista',
    }
    normalized_role = aliases.get(role_name, role_name)
    normalized_candidates = [aliases.get(c, c) for c in candidates]
    return normalized_role in normalized_candidates


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser


class IsTenantAdmin(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False

        tenant = _resolve_permission_tenant(request)
        return get_effective_role_name(user, tenant=tenant) in {'SuperAdmin', 'Client-Admin'}


class IsTenantMember(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        tenant = getattr(request, 'tenant', request.user.tenant if hasattr(request.user, 'tenant') else None)
        return tenant is not None


class RolePermission(BasePermission):
    """
    Permite acceso si el usuario tiene alguno de los roles permitidos.
    Usa caché en request para evitar queries repetidas.
    Soporta alias de roles (Admin → Client-Admin, Stylist → Estilista).
    """

    def __init__(self, allowed_roles=None):
        self.allowed_roles = allowed_roles or []

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        if not hasattr(request, '_cached_roles'):
            tenant = _resolve_permission_tenant(request)
            roles_qs = UserRole.objects.filter(user=request.user)
            if tenant is not None:
                roles_qs = roles_qs.filter(tenant=tenant)
            request._cached_roles = set(roles_qs.values_list('role__name', flat=True))

        return any(_matches_role(role, *self.allowed_roles) for role in request._cached_roles)


def role_permission_for(roles):
    """
    Genera dinámicamente un permiso específico para los roles indicados.
    """
    def __init__(self):
        RolePermission.__init__(self, allowed_roles=roles)

    return type(
        f'RolePermissionFor{"_".join(roles)}',
        (RolePermission,),
        {
            '__init__': __init__
        }
    )
