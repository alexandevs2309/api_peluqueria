"""
Base ViewSet para filtrado automático por tenant
"""
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers


class TenantQuerySetMixin:
    """Mixin con lógica de filtrado por tenant compartida entre ViewSets."""

    def _resolve_tenant(self):
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return tenant
        user = getattr(self.request, 'user', None)
        if user and hasattr(user, 'tenant') and not user.is_superuser:
            return user.tenant
        return None

    def get_queryset(self):
        queryset = super().get_queryset()

        tenant = self._resolve_tenant()

        if self.request.user.is_superuser:
            if tenant:
                queryset = queryset.filter(tenant=tenant)
            else:
                # SuperAdmin sin tenant en request: filtro opcional por ?tenant=<id>
                tenant_id = self.request.query_params.get('tenant')
                if tenant_id:
                    queryset = queryset.filter(tenant_id=tenant_id)
        elif not tenant:
            return queryset.none()
        else:
            queryset = queryset.filter(tenant=tenant)

        # Filtrado opcional por sucursal si el modelo la soporta
        branch_id = self.request.query_params.get('branch_id') or self.request.query_params.get('branch')
        
        if tenant and not tenant.has_feature('multi_location'):
            branch_id = None
        
        # Restricción estricta de sucursal para empleados no administradores
        user = self.request.user
        if user and getattr(user, 'is_authenticated', False) and not user.is_superuser:
            user_role = getattr(self.request, '_role_cache', None)
            if user_role is None:
                from apps.auth_api.role_utils import get_effective_role_api
                user_role = get_effective_role_api(user, tenant=tenant)
                setattr(self.request, '_role_cache', user_role)
            if user_role != 'CLIENT_ADMIN' and hasattr(user, 'employee_profile') and user.employee_profile:
                if user.employee_profile.branch_id:
                    branch_id = user.employee_profile.branch_id

        if branch_id:
            from django.core.exceptions import FieldDoesNotExist
            try:
                queryset.model._meta.get_field('branch')
                if queryset.model.__name__ in ('Employee', 'Service'):
                    from django.db.models import Q
                    queryset = queryset.filter(Q(branch_id=branch_id) | Q(branch__isnull=True))
                else:
                    queryset = queryset.filter(branch_id=branch_id)
            except FieldDoesNotExist:
                pass

        return queryset


class TenantScopedViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
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

    def perform_create(self, serializer):
        user = self.request.user

        if user.is_superuser:
            tenant = getattr(self.request, 'tenant', None)  # solo request.tenant, sin fallback
            if tenant:
                serializer.save(tenant=tenant)
            else:
                serializer.save()  # superuser sin tenant: guarda sin filtro (o tenant explícito si se pasa)
            return

        tenant = self._resolve_tenant()
        if not tenant:
            raise serializers.ValidationError({"detail": "Usuario sin tenant asignado"})

        save_kwargs = {'tenant': tenant}

        # Restricción/Autoset de sucursal para empleados no administradores
        if user and getattr(user, 'is_authenticated', False):
            user_role = getattr(self.request, '_role_cache', None)
            if user_role is None:
                from apps.auth_api.role_utils import get_effective_role_api
                user_role = get_effective_role_api(user, tenant=tenant)
                setattr(self.request, '_role_cache', user_role)
            if user_role != 'CLIENT_ADMIN' and hasattr(user, 'employee_profile') and user.employee_profile:
                if user.employee_profile.branch_id:
                    if hasattr(serializer, 'Meta') and hasattr(serializer.Meta, 'model'):
                        from django.core.exceptions import FieldDoesNotExist
                        try:
                            serializer.Meta.model._meta.get_field('branch')
                            branch_val = serializer.validated_data.get('branch')
                            if branch_val and branch_val.id != user.employee_profile.branch_id:
                                raise PermissionDenied("No tienes permisos para operar en una sucursal distinta a la tuya")
                            save_kwargs['branch_id'] = user.employee_profile.branch_id
                        except FieldDoesNotExist:
                            pass

        serializer.save(**save_kwargs)

    def perform_update(self, serializer):
        user = self.request.user

        # Restricción de sucursal para empleados no administradores en actualizaciones
        if user and getattr(user, 'is_authenticated', False) and not user.is_superuser:
            from apps.auth_api.role_utils import get_effective_role_api
            tenant = self._resolve_tenant()
            if tenant:
                user_role = get_effective_role_api(user, tenant=tenant)
                if user_role != 'CLIENT_ADMIN' and hasattr(user, 'employee_profile') and user.employee_profile:
                    if user.employee_profile.branch_id:
                        if hasattr(serializer, 'Meta') and hasattr(serializer.Meta, 'model'):
                            from django.core.exceptions import FieldDoesNotExist
                            try:
                                serializer.Meta.model._meta.get_field('branch')
                                branch_val = serializer.validated_data.get('branch')
                                if branch_val and branch_val.id != user.employee_profile.branch_id:
                                    raise PermissionDenied("No tienes permisos para operar en una sucursal distinta a la tuya")
                            except FieldDoesNotExist:
                                pass

        serializer.save()


class TenantScopedReadOnlyViewSet(TenantQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    """
    Versión ReadOnly de TenantScopedViewSet.
    
    Uso:
        class MyViewSet(TenantScopedReadOnlyViewSet):
            queryset = MyModel.objects.all()
            serializer_class = MySerializer
    """
