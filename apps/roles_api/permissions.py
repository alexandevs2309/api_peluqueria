from rest_framework.permissions import BasePermission
from apps.roles_api.models import UserRole

# Re-export unificado desde core.permissions
from apps.core.permissions import RolePermission, role_permission_for

__all__ = ["RolePermission", "role_permission_for", "IsActiveAndRolePermission"]


class IsActiveAndRolePermission(BasePermission):
    def __init__(self, allowed_roles):
        self.allowed_roles = allowed_roles

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated or not request.user.is_active:
            return False

        if not hasattr(request, '_cached_roles'):
            if hasattr(request, 'current_tenant') and request.current_tenant:
                request._cached_roles = set(
                    UserRole.objects.filter(user=request.user, tenant=request.current_tenant).values_list('role__name', flat=True)
                )
            else:
                request._cached_roles = set(
                    UserRole.objects.filter(user=request.user, tenant__isnull=True).values_list('role__name', flat=True)
                )

        return bool(set(self.allowed_roles) & request._cached_roles)
