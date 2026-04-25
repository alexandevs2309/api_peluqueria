"""
Permisos adicionales para control de acceso por rol
"""
from rest_framework.permissions import BasePermission
from apps.auth_api.role_utils import get_effective_role_name


class IsAdminRole(BasePermission):
    """
    Solo Client-Admin o SuperAdmin
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return get_effective_role_name(
            request.user,
            tenant=getattr(request, 'tenant', None),
        ) in ['Client-Admin', 'SuperAdmin']


class CanManageUsers(BasePermission):
    """
    Solo roles que pueden gestionar usuarios
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return get_effective_role_name(
            request.user,
            tenant=getattr(request, 'tenant', None),
        ) in ['Client-Admin', 'Manager', 'SuperAdmin']


class IsReadOnlyOrAdmin(BasePermission):
    """
    Lectura para todos, escritura solo para admins
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Lectura permitida para todos
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Escritura solo para admins
        return get_effective_role_name(
            request.user,
            tenant=getattr(request, 'tenant', None),
        ) in ['Client-Admin', 'Manager', 'SuperAdmin']
