from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied


class TenantScopedModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet que garantiza aislamiento multi-tenant.
    
    - SuperAdmin (is_superuser=True): Acceso total sin filtros
    - Usuarios con tenant: Solo datos de su tenant
    - Usuarios sin tenant: Sin acceso (queryset vacío)
    """
    queryset = None  # Forzar override en subclases
    
    def get_queryset(self):
        if self.queryset is None:
            raise NotImplementedError("Subclass must define queryset")
        
        qs = self.queryset
        user = self.request.user
        
        # SuperAdmin: acceso total
        if user.is_superuser:
            return qs
        
        # Usuario sin tenant: sin acceso
        if not hasattr(self.request, 'tenant') or not self.request.tenant:
            return qs.none()
        
        # Filtrar por tenant del request
        return self._filter_by_tenant(qs, self.request.tenant)
    
    def _filter_by_tenant(self, queryset, tenant):
        """
        Override este método si el modelo usa un campo diferente a 'tenant'.
        Ejemplo: return queryset.filter(client__tenant=tenant)
        """
        return queryset.filter(tenant=tenant)
    
    def perform_create(self, serializer):
        """Asignar tenant automáticamente en creación"""
        user = self.request.user
        
        # SuperAdmin puede crear sin tenant o con tenant explícito
        if user.is_superuser:
            if 'tenant' not in serializer.validated_data:
                serializer.save()
            else:
                serializer.save()
            return
        
        # Usuario normal: forzar tenant del request
        if not hasattr(self.request, 'tenant') or not self.request.tenant:
            raise PermissionDenied("Usuario sin tenant asignado")
        
        serializer.save(tenant=self.request.tenant)
