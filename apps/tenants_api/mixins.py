from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, ValidationError

class TenantFilterMixin:
    """
    Mixin para filtrar automáticamente por tenant usando middleware
    """
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # SuperAdmin puede ver todo
        if user.is_superuser or user.roles.filter(name='Super-Admin').exists():
            return queryset
            
        # Usar tenant del middleware
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            # Verificar nivel de acceso
            access_level = tenant.get_access_level()
            if access_level == 'blocked':
                return queryset.none()
            
            return queryset.filter(tenant=tenant)
            
        # Fallback: usar tenant del usuario
        if hasattr(user, 'tenant') and user.tenant:
            return queryset.filter(tenant=user.tenant)
            
        # Sin tenant = sin datos
        return queryset.none()
    
    def check_write_permissions(self):
        """Verificar permisos de escritura"""
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            access_level = tenant.get_access_level()
            if access_level in ['blocked', 'grace']:
                if access_level == 'grace':
                    message = 'Your trial has expired. You have 3 days to subscribe before losing access.'
                else:
                    message = 'Your access has been blocked. Please subscribe to continue.'
                
                raise PermissionDenied({
                    'error': 'Subscription required',
                    'code': 'SUBSCRIPTION_REQUIRED',
                    'message': message,
                    'upgrade_url': '/subscriptions/upgrade/',
                    'access_level': access_level
                })
    
    def perform_create(self, serializer):
        user = self.request.user
        
        # SuperAdmin puede crear para cualquier tenant
        if user.is_superuser or user.roles.filter(name='Super-Admin').exists():
            return super().perform_create(serializer)
            
        # Verificar permisos de escritura
        self.check_write_permissions()
            
        # Usar tenant del middleware
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            raise ValidationError("Usuario sin tenant asignado")
            
        serializer.save(tenant=tenant)

class TenantPermissionMixin:
    """
    Mixin para validar permisos por tenant con middleware
    """
    
    def check_tenant_permission(self, obj):
        user = self.request.user
        
        # SuperAdmin puede acceder a todo
        if user.is_superuser or user.roles.filter(name='Super-Admin').exists():
            return True
            
        # Verificar que el objeto pertenece al tenant del usuario
        tenant = getattr(self.request, 'tenant', None)
        if hasattr(obj, 'tenant') and obj.tenant != tenant:
            raise PermissionDenied("No tienes permisos para acceder a este recurso")
            
        return True
    
    def get_object(self):
        obj = super().get_object()
        self.check_tenant_permission(obj)
        return obj
        
    def perform_update(self, serializer):
        # Verificar permisos de escritura si es TenantFilterMixin
        if hasattr(self, 'check_write_permissions'):
            self.check_write_permissions()
        instance = self.get_object()  # Ya valida permisos
        super().perform_update(serializer)
        
    def perform_destroy(self, instance):
        # Verificar permisos de escritura si es TenantFilterMixin
        if hasattr(self, 'check_write_permissions'):
            self.check_write_permissions()
        self.check_tenant_permission(instance)
        super().perform_destroy(instance)