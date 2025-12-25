"""
Permiso compuesto para endpoints que requieren acceso tanto de SUPER_ADMIN como de usuarios CLIENT
"""
from rest_framework.permissions import BasePermission
from apps.roles_api.models import UserRole


class IsSuperAdminOrClientUser(BasePermission):
    """
    Permite acceso a:
    - SUPER_ADMIN (sin tenant, acceso global)
    - CLIENT_ADMIN y CLIENT_STAFF (con tenant, acceso limitado)
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # SUPER_ADMIN: acceso global
        if UserRole.objects.filter(
            user=request.user,
            role__name='SUPER_ADMIN'
        ).exists():
            return True
        
        # CLIENT_ADMIN o CLIENT_STAFF: acceso limitado (requiere tenant del usuario)
        if not request.user.tenant:
            return False
            
        return UserRole.objects.filter(
            user=request.user,
            role__name__in=['CLIENT_ADMIN', 'CLIENT_STAFF'],
            tenant=request.user.tenant
        ).exists()