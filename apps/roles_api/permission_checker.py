from django.contrib.auth.models import Permission
from .models import UserRole

class PermissionChecker:
    
    @staticmethod
    def user_has_permission(user, permission_codename, tenant=None):
        """Verifica si el usuario tiene un permiso específico"""
        user_roles = UserRole.objects.filter(user=user)
        
        # Filtrar por tenant si es necesario
        if tenant:
            user_roles = user_roles.filter(tenant=tenant)
        
        for user_role in user_roles:
            role = user_role.role
            
            # Verificar permisos Django
            if role.permissions.filter(codename=permission_codename).exists():
                return True
                
            # Verificar límites personalizados
            if permission_codename in role.limits.get('permissions', []):
                return True
                
        return False
    
    @staticmethod
    def user_can_access_module(user, module_name, tenant=None):
        """Verifica si el usuario puede acceder a un módulo"""
        user_roles = UserRole.objects.filter(user=user)
        
        if tenant:
            user_roles = user_roles.filter(tenant=tenant)
            
        for user_role in user_roles:
            role = user_role.role
            
            # Roles GLOBAL pueden acceder a todo
            if role.scope == 'GLOBAL':
                return True
                
            # Verificar módulos permitidos en limits
            allowed_modules = role.limits.get('modules', [])
            if module_name in allowed_modules:
                return True
                
        return False
    
    @staticmethod
    def get_user_limits(user, tenant=None):
        """Obtiene los límites del usuario"""
        user_roles = UserRole.objects.filter(user=user)
        
        if tenant:
            user_roles = user_roles.filter(tenant=tenant)
            
        limits = {}
        
        for user_role in user_roles:
            role = user_role.role
            
            # Combinar límites de todos los roles
            for key, value in role.limits.items():
                if key not in limits:
                    limits[key] = value
                elif isinstance(value, int) and isinstance(limits[key], int):
                    # Tomar el límite más alto
                    limits[key] = max(limits[key], value)
                elif isinstance(value, list):
                    # Combinar listas
                    limits[key] = list(set(limits[key] + value))
                    
        return limits