"""Sistema de permisos centralizado - ENDURECIDO
Acciones críticas son responsabilidades EXCLUSIVAS de CLIENT_ADMIN
"""
from rest_framework.permissions import BasePermission
from apps.roles_api.models import UserRole


class IsSuperAdmin(BasePermission):
    """Solo SUPER_ADMIN - SOLO LECTURA para soporte"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # SUPER_ADMIN solo métodos GET
        if request.method not in ['GET', 'HEAD', 'OPTIONS']:
            return False
        return UserRole.objects.filter(
            user=request.user,
            role__name='SUPER_ADMIN'
        ).exists()


class IsClientAdmin(BasePermission):
    """Solo CLIENT_ADMIN - acceso completo operativo"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return UserRole.objects.filter(
            user=request.user,
            role__name='CLIENT_ADMIN'
        ).exists()


class IsClientAdminOrStaff(BasePermission):
    """CLIENT_ADMIN o STAFF - operaciones básicas"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return UserRole.objects.filter(
            user=request.user,
            role__name__in=['CLIENT_ADMIN', 'CLIENT_STAFF']
        ).exists()


class IsEmployeeReadOnly(BasePermission):
    """EMPLOYEE - solo lectura de su propio balance"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # Solo métodos GET
        if request.method not in ['GET', 'HEAD', 'OPTIONS']:
            return False
        return UserRole.objects.filter(
            user=request.user,
            role__name='CLIENT_STAFF'
        ).exists()


class CanViewFinancialData(BasePermission):
    """CLIENT_ADMIN y SUPER_ADMIN (solo lectura) pueden ver datos financieros"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # SUPER_ADMIN solo lectura
        if UserRole.objects.filter(user=request.user, role__name='SUPER_ADMIN').exists():
            return request.method in ['GET', 'HEAD', 'OPTIONS']
        
        # CLIENT_ADMIN acceso completo
        return UserRole.objects.filter(
            user=request.user,
            role__name='CLIENT_ADMIN'
        ).exists()