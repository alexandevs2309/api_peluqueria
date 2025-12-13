"""
Permisos para módulo de nómina
"""
from rest_framework import permissions

class IsHROrClientAdmin(permissions.BasePermission):
    """Solo RRHH o Client-Admin pueden generar nómina"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Superuser siempre tiene acceso
        if request.user.is_superuser:
            return True
        
        # Verificar roles
        user_roles = request.user.user_roles.values_list('role__name', flat=True)
        return 'Client-Admin' in user_roles or 'HR' in user_roles

class CanViewOwnPaystubs(permissions.BasePermission):
    """Empleados solo pueden ver sus propios recibos"""
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        # Verificar si es el empleado dueño
        if hasattr(obj, 'employee'):
            return obj.employee.user == request.user
        
        return False
