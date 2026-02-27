from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from .models import UserRole

User = get_user_model()

class RoleBasedPermissionBackend(BaseBackend):
    """
    Backend de autenticación que permite verificar permisos basados en roles personalizados
    
    IMPORTANTE: Este backend NO filtra por tenant porque no tiene acceso a request.
    El filtrado por tenant se hace en DRF permission classes.
    
    Usar solo para validaciones programáticas donde el tenant ya está validado.
    """
    
    def authenticate(self, request, **kwargs):
        # Este backend no maneja autenticación, solo permisos
        return None
    
    def has_perm(self, user_obj, perm, obj=None):
        """
        Verifica si el usuario tiene el permiso específico a través de sus roles
        Filtra por tenant si está disponible en el contexto
        """
        if not user_obj.is_active:
            return False
            
        # SuperAdmin tiene todos los permisos
        if user_obj.is_superuser:
            return True
        
        # Parsear permiso correctamente
        if '.' not in perm:
            return False
        
        app_label, codename = perm.split('.', 1)
        
        # Obtener tenant del usuario (no del request, backend no tiene acceso)
        # El filtrado por tenant se hace en la permission class de DRF
        user_roles = UserRole.objects.filter(
            user=user_obj
        ).select_related('role').prefetch_related('role__permissions__content_type')
        
        for user_role in user_roles:
            role = user_role.role
            # Verificar permiso con app_label + codename
            if role.permissions.filter(
                content_type__app_label=app_label,
                codename=codename
            ).exists():
                return True
                
        return False
    
    def has_module_perms(self, user_obj, app_label):
        """
        Verifica si el usuario tiene permisos para un módulo específico
        """
        if not user_obj.is_active:
            return False
            
        if user_obj.is_superuser:
            return True
            
        # Verificar si tiene algún permiso en el módulo a través de roles
        user_roles = UserRole.objects.filter(user=user_obj).select_related('role')
        
        for user_role in user_roles:
            role = user_role.role
            if role.permissions.filter(content_type__app_label=app_label).exists():
                return True
                
        return False
    
    def get_user_permissions(self, user_obj, obj=None):
        """
        Retorna todos los permisos del usuario a través de sus roles
        """
        if not user_obj.is_active:
            return set()
        
        user_roles = UserRole.objects.filter(
            user=user_obj
        ).select_related('role').prefetch_related('role__permissions__content_type')
        
        permissions = set()
        for user_role in user_roles:
            role = user_role.role
            role_perms = role.permissions.select_related('content_type').values_list(
                'content_type__app_label', 'codename'
            )
            for app_label, codename in role_perms:
                permissions.add(f'{app_label}.{codename}')
                
        return permissions
    
    def get_group_permissions(self, user_obj, obj=None):
        """
        No usamos grupos de Django, retornamos set vacío
        """
        return set()
    
    def get_all_permissions(self, user_obj, obj=None):
        """
        Retorna todos los permisos del usuario (roles + permisos directos)
        """
        if not user_obj.is_active:
            return set()
            
        if user_obj.is_superuser:
            from django.contrib.auth.models import Permission
            return set(f'{p.content_type.app_label}.{p.codename}' for p in Permission.objects.all())
            
        return self.get_user_permissions(user_obj, obj)