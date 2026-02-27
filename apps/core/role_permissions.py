"""
Permisos adicionales para control de acceso por rol
"""
from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """
    Solo Client-Admin o SuperAdmin
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        return request.user.role in ['Client-Admin', 'SuperAdmin', 'Super-Admin']


class CanManageUsers(BasePermission):
    """
    Solo roles que pueden gestionar usuarios
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Solo Client-Admin y Manager pueden gestionar usuarios
        return request.user.role in ['Client-Admin', 'Manager']


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
        if request.user.is_superuser:
            return True
        
        return request.user.role in ['Client-Admin', 'Manager']
