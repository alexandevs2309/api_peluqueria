from rest_framework import permissions
from apps.auth_api.role_utils import get_effective_role_name
from apps.core.permissions import _matches_role, _resolve_permission_tenant

# Re-export unificado desde core.permissions
from apps.core.permissions import RolePermission, role_permission_for

__all__ = ["RolePermission", "role_permission_for", "IsAdminOrOwnStylist"]


class IsAdminOrOwnStylist(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        tenant = _resolve_permission_tenant(request)
        role_name = get_effective_role_name(request.user, tenant=tenant)
        if hasattr(view, 'action') and view.action in ['create', 'update', 'partial_update', 'destroy']:
            return _matches_role(role_name, 'Admin', 'Client-Admin')
        return _matches_role(role_name, 'Admin', 'Client-Admin', 'Stylist', 'Estilista')

    def has_object_permission(self, request, view, obj):
        tenant = _resolve_permission_tenant(request)
        role_name = get_effective_role_name(request.user, tenant=tenant)
        if _matches_role(role_name, 'Admin', 'Client-Admin'):
            return True
        return obj.user == request.user
