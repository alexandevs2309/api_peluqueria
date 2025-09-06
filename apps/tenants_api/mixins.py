from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

class TenantFilterMixin:
    """
    Mixin para filtrar automáticamente por tenant del usuario logueado
    """
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # SuperAdmin puede ver todo
        if user.is_superuser:
            return queryset
            
        # Usuario debe tener tenant
        if not user.tenant:
            return queryset.none()
            
        # Filtrar por tenant del usuario
        return queryset.filter(tenant=user.tenant)
    
    def perform_create(self, serializer):
        user = self.request.user
        
        # SuperAdmin puede crear para cualquier tenant
        if user.is_superuser:
            return super().perform_create(serializer)
            
        # Usuario normal solo puede crear para su tenant
        if not user.tenant:
            raise PermissionDenied("Usuario sin tenant asignado")
            
        serializer.save(tenant=user.tenant)

class TenantPermissionMixin:
    """
    Mixin para validar permisos por tenant
    """
    
    def check_tenant_permission(self, obj):
        user = self.request.user
        
        # SuperAdmin puede acceder a todo
        if user.is_superuser:
            return True
            
        # Verificar que el objeto pertenece al tenant del usuario
        if hasattr(obj, 'tenant') and obj.tenant != user.tenant:
            raise PermissionDenied("No tienes permisos para acceder a este recurso")
            
        return True
    
    def get_object(self):
        obj = super().get_object()
        self.check_tenant_permission(obj)
        return obj