"""
Permisos centralizados para el sistema multi-tenant.
Evita duplicación de permisos comunes en múltiples apps.
"""
from rest_framework.permissions import BasePermission


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
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        return request.user.role == 'Client-Admin'


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
