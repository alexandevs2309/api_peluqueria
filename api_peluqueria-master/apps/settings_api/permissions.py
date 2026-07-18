from rest_framework.permissions import BasePermission
from apps.auth_api.role_utils import get_effective_role_name


class IsClientAdmin(BasePermission):
    """Permission para CLIENT_ADMIN solamente"""
    
    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False

        tenant = getattr(request, 'tenant', None)
        if tenant is None:
            tenant = getattr(user, 'tenant', None)

        return get_effective_role_name(user, tenant=tenant) in {'SuperAdmin', 'Client-Admin'}
