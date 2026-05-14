from django.contrib.auth.models import Permission
from .models import UserRole

class PermissionChecker:
    
    @staticmethod
    def user_has_permission(user, permission_codename, tenant=None):
        """Verifica si el usuario tiene un permiso específico"""
        user_roles = UserRole.objects.filter(user=user).select_related('role').prefetch_related('role__permissions')
        
        if tenant:
            user_roles = user_roles.filter(tenant=tenant)
        
        for user_role in user_roles:
            role = user_role.role
            
            if role.permissions.filter(codename=permission_codename).exists():
                return True
                
            if permission_codename in role.limits.get('permissions', []):
                return True
                
        return False
    
    @staticmethod
    def user_can_access_module(user, module_name, tenant=None):
        """Verifica si el usuario puede acceder a un módulo"""
        user_roles = UserRole.objects.filter(user=user).select_related('role')
        
        if tenant:
            user_roles = user_roles.filter(tenant=tenant)
            
        for user_role in user_roles:
            role = user_role.role
            
            if role.scope == 'GLOBAL':
                return True
                
            allowed_modules = role.limits.get('modules', [])
            if module_name in allowed_modules:
                return True
                
        return False
    
    @staticmethod
    def get_user_limits(user, tenant=None):
        """Obtiene los límites del usuario"""
        user_roles = UserRole.objects.filter(user=user).select_related('role')
        
        if tenant:
            user_roles = user_roles.filter(tenant=tenant)
            
        limits = {}
        
        for user_role in user_roles:
            role = user_role.role
            
            for key, value in role.limits.items():
                if key not in limits:
                    limits[key] = value
                elif isinstance(value, int) and isinstance(limits[key], int):
                    limits[key] = max(limits[key], value)
                elif isinstance(value, list):
                    limits[key] = list(set(limits[key] + value))
                    
        return limits