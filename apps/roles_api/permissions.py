from rest_framework.permissions import BasePermission
from .models import UserRole

class RolePermission(BasePermission):
    """
    Verifica si el usuario tiene uno de los roles permitidos.
    """
    def __init__(self, allowed_roles=None):
        self.allowed_roles = allowed_roles or []

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        if not hasattr(request, '_cached_roles'):
            request._cached_roles = set(
                request.user.roles.values_list('name', flat=True)
            )

        return bool(set(self.allowed_roles) & request._cached_roles)

def role_permission_for(roles):
    """
    Genera dinámicamente un permiso específico para los roles indicados.
    """
    return type(
        f'RolePermissionFor{"_".join(roles)}',
        (RolePermission,),
        {
            '__init__': lambda self: RolePermission.__init__(self, allowed_roles=roles)
        }
    )

class IsActiveAndRolePermission(BasePermission):
    """
    Verifica que el usuario esté activo y tenga uno de los roles permitidos.
    """
    def __init__(self, allowed_roles):
        self.allowed_roles = allowed_roles

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated or not request.user.is_active:
            return False

        if not hasattr(request, '_cached_roles'):
            request._cached_roles = set(
                request.user.roles.values_list('name', flat=True)
            )

        return bool(set(self.allowed_roles) & request._cached_roles)
