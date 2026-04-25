from rest_framework import permissions
from apps.auth_api.role_utils import get_effective_role_name


def _resolve_tenant(request):
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
    normalized = aliases.get(role_name, role_name)
    return normalized in candidates

class RolePermission(permissions.BasePermission):
    def __init__(self, allowed_roles=None):
        self.allowed_roles = allowed_roles or []

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        tenant = _resolve_tenant(request)
        role_name = get_effective_role_name(request.user, tenant=tenant)
        return any(_matches_role(role_name, role) for role in self.allowed_roles)

def role_permission_for(roles):
    return type(
        f'RolePermissionFor{"_".join(roles)}',
        (RolePermission,),
        {
            '__init__': lambda self: RolePermission.__init__(self, allowed_roles=roles)
        }
    )

class IsAdminOrOwnStylist(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        tenant = _resolve_tenant(request)
        role_name = get_effective_role_name(request.user, tenant=tenant)
        # Permitir solo a Admin para crear o modificar
        if hasattr(view, 'action') and view.action in ['create', 'update', 'partial_update', 'destroy']:
            return _matches_role(role_name, 'Admin', 'Client-Admin')
        # Para otras acciones permitir Admin o Stylist
        return _matches_role(role_name, 'Admin', 'Client-Admin', 'Stylist', 'Estilista')

    def has_object_permission(self, request, view, obj):
        tenant = _resolve_tenant(request)
        role_name = get_effective_role_name(request.user, tenant=tenant)
        if _matches_role(role_name, 'Admin', 'Client-Admin'):
            return True
        return obj.user == request.user
