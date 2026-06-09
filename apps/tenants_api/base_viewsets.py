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
                queryset = queryset.filter(tenant=tenant)
        elif not hasattr(self.request, 'tenant') or not self.request.tenant:
            return queryset.none()
        else:
            queryset = queryset.filter(tenant=self.request.tenant)

        # Filtrado opcional por sucursal si el modelo la soporta
        branch_id = self.request.query_params.get('branch_id') or self.request.query_params.get('branch')
        
        # Restricción estricta de sucursal para empleados no administradores
        user = self.request.user
        if user and getattr(user, 'is_authenticated', False) and not user.is_superuser:
            from apps.auth_api.role_utils import get_effective_role_api
            user_role = get_effective_role_api(user, tenant=self.request.tenant)
            if user_role != 'Client-Admin' and hasattr(user, 'employee_profile') and user.employee_profile:
                if user.employee_profile.branch_id:
                    branch_id = user.employee_profile.branch_id

        if branch_id:
            from django.core.exceptions import FieldDoesNotExist
            try:
                queryset.model._meta.get_field('branch')
                queryset = queryset.filter(branch_id=branch_id)
            except FieldDoesNotExist:
                pass

        return queryset

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

        save_kwargs = {'tenant': self.request.tenant}

        # Restricción/Autoset de sucursal para empleados no administradores
        if user and getattr(user, 'is_authenticated', False):
            from apps.auth_api.role_utils import get_effective_role_api
            user_role = get_effective_role_api(user, tenant=self.request.tenant)
            if user_role != 'Client-Admin' and hasattr(user, 'employee_profile') and user.employee_profile:
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
            tenant = getattr(self.request, 'tenant', None) or getattr(user, 'tenant', None)
            if tenant:
                user_role = get_effective_role_api(user, tenant=tenant)
                if user_role != 'Client-Admin' and hasattr(user, 'employee_profile') and user.employee_profile:
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
                queryset = queryset.filter(tenant=tenant)
        elif not hasattr(self.request, 'tenant') or not self.request.tenant:
            return queryset.none()
        else:
            queryset = queryset.filter(tenant=self.request.tenant)

        # Filtrado opcional por sucursal si el modelo la soporta
        branch_id = self.request.query_params.get('branch_id') or self.request.query_params.get('branch')
        
        # Restricción estricta de sucursal para empleados no administradores
        user = self.request.user
        if user and getattr(user, 'is_authenticated', False) and not user.is_superuser:
            from apps.auth_api.role_utils import get_effective_role_api
            user_role = get_effective_role_api(user, tenant=self.request.tenant)
            if user_role != 'Client-Admin' and hasattr(user, 'employee_profile') and user.employee_profile:
                if user.employee_profile.branch_id:
                    branch_id = user.employee_profile.branch_id

        if branch_id:
            from django.core.exceptions import FieldDoesNotExist
            try:
                queryset.model._meta.get_field('branch')
                queryset = queryset.filter(branch_id=branch_id)
            except FieldDoesNotExist:
                pass

        return queryset
