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
    - request.tenant debe estar seteado por middleware
    """
    
    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.user.is_superuser:
            tenant = getattr(self.request, 'tenant', None)
            if tenant:
                return queryset.filter(tenant=tenant)
            return queryset

        if not hasattr(self.request, 'tenant') or not self.request.tenant:
            return queryset.none()

        return queryset.filter(tenant=self.request.tenant)

    def perform_create(self, serializer):
        user = self.request.user

        if user.is_superuser:
            tenant = getattr(self.request, 'tenant', None)
            if tenant:
                serializer.save(tenant=tenant)
            else:
                serializer.save()
            return

        if not hasattr(self.request, 'tenant') or not self.request.tenant:
            raise PermissionDenied("Usuario sin tenant asignado")

        serializer.save(tenant=self.request.tenant)


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

        if self.request.user.is_superuser:
            tenant = getattr(self.request, 'tenant', None)
            if tenant:
                return queryset.filter(tenant=tenant)
            return queryset

        if not hasattr(self.request, 'tenant') or not self.request.tenant:
            return queryset.none()

        return queryset.filter(tenant=self.request.tenant)
