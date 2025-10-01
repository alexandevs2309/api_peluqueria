from django.core.exceptions import PermissionDenied
from rest_framework.exceptions import NotFound

class TenantFilterMixin:
    """
    Mixin que automáticamente filtra querysets por tenant del usuario autenticado
    """
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Superusuarios pueden ver todo
        if self.request.user.is_superuser:
            return queryset
            
        # Usuarios sin tenant no pueden ver nada
        if not hasattr(self.request.user, 'tenant') or not self.request.user.tenant:
            return queryset.none()
            
        # Filtrar por tenant del usuario
        if hasattr(queryset.model, 'tenant'):
            return queryset.filter(tenant=self.request.user.tenant)
        
        return queryset
    
    def perform_create(self, serializer):
        """Asignar automáticamente el tenant al crear objetos"""
        if hasattr(serializer.Meta.model, 'tenant') and self.request.user.tenant:
            serializer.save(tenant=self.request.user.tenant)
        else:
            serializer.save()
    
    def get_object(self):
        """Validar que el objeto pertenece al tenant del usuario"""
        obj = super().get_object()
        
        # Superusuarios pueden acceder a todo
        if self.request.user.is_superuser:
            return obj
            
        # Validar tenant si el modelo lo tiene
        if hasattr(obj, 'tenant'):
            if not self.request.user.tenant or obj.tenant != self.request.user.tenant:
                raise NotFound("Objeto no encontrado")
        
        return obj

class TenantRequiredMixin:
    """
    Mixin que requiere que el usuario tenga un tenant asignado
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            if not hasattr(request.user, 'tenant') or not request.user.tenant:
                raise PermissionDenied("Usuario debe tener un tenant asignado")
        return super().dispatch(request, *args, **kwargs)