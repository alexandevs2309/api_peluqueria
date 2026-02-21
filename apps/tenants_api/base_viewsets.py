"""
Base ViewSet para filtrado automático por tenant
"""
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied


class TenantScopedViewSet(viewsets.ModelViewSet):
    """
    ViewSet base que filtra automáticamente por tenant.
    
    Comportamiento:
    - SuperAdmin: Ve todos los registros
    - Usuario con tenant: Ve solo registros de su tenant
    - Usuario sin tenant: No ve nada
    
    Uso:
        class MyViewSet(TenantScopedViewSet):
            queryset = MyModel.objects.all()
            serializer_class = MySerializer
            
            # get_queryset() ya está implementado
    
    Requisitos:
    - El modelo debe tener campo 'tenant' (ForeignKey a Tenant)
    - El usuario debe tener atributo 'tenant'
    """
    
    def get_queryset(self):
        """
        Filtra queryset por tenant automáticamente.
        
        Override este método si necesitas lógica adicional:
            def get_queryset(self):
                qs = super().get_queryset()
                # Lógica adicional aquí
                return qs
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        # SuperAdmin ve todo
        if user.is_superuser:
            return queryset
        
        # Usuario sin tenant no ve nada
        if not hasattr(user, 'tenant') or not user.tenant:
            return queryset.none()
        
        # Filtrar por tenant del usuario
        return queryset.filter(tenant=user.tenant)
    
    def perform_create(self, serializer):
        """
        Asigna tenant automáticamente al crear.
        
        Override si necesitas lógica adicional:
            def perform_create(self, serializer):
                super().perform_create(serializer)
                # Lógica adicional aquí
        """
        user = self.request.user
        
        # SuperAdmin puede crear para cualquier tenant
        if user.is_superuser:
            # Si no especifica tenant, usar el primero disponible
            if 'tenant' not in serializer.validated_data:
                from apps.tenants_api.models import Tenant
                tenant = user.tenant or Tenant.objects.first()
                serializer.save(tenant=tenant)
            else:
                serializer.save()
            return
        
        # Usuario normal debe tener tenant
        if not user.tenant:
            raise PermissionDenied("Usuario sin tenant asignado")
        
        # Asignar tenant del usuario
        serializer.save(tenant=user.tenant)


class TenantScopedReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Versión ReadOnly de TenantScopedViewSet.
    
    Uso:
        class MyViewSet(TenantScopedReadOnlyViewSet):
            queryset = MyModel.objects.all()
            serializer_class = MySerializer
    """
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.is_superuser:
            return queryset
        
        if not hasattr(user, 'tenant') or not user.tenant:
            return queryset.none()
        
        return queryset.filter(tenant=user.tenant)
