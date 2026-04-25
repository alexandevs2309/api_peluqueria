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


class IsSuperAdmin(BasePermission):
    """
    Permiso que solo permite acceso a SuperAdmin.
    Usado en endpoints administrativos globales.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser


class IsTenantAdmin(BasePermission):
    """
    Permiso que permite acceso a Client-Admin o SuperAdmin.
    Usado en endpoints de gestión del tenant.
    """
    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        
        tenant = _resolve_permission_tenant(request)
        return get_effective_role_name(user, tenant=tenant) in {'SuperAdmin', 'Client-Admin'}


class IsTenantMember(BasePermission):
    """
    Permiso que permite acceso a cualquier usuario con tenant asignado.
    SuperAdmin también tiene acceso.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        return hasattr(request.user, 'tenant') and request.user.tenant is not None


class RolePermission(BasePermission):
    """
    Permite acceso si el usuario tiene alguno de los roles permitidos.
    Configurar allowed_roles en la clase que hereda.
    """
    allowed_roles = ['Admin']

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        tenant = _resolve_permission_tenant(request)
        user_roles = UserRole.objects.filter(user=request.user)
        if tenant is not None:
            user_roles = user_roles.filter(tenant=tenant)

        user_roles = user_roles.values_list('role__name', flat=True)
        return any(role in self.allowed_roles for role in user_roles)
