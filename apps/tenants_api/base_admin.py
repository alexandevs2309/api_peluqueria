"""
Base Admin classes para filtrado automático por tenant.
Mantiene compatibilidad con comportamiento actual.
"""
from django.contrib import admin
from django.core.exceptions import FieldError


class BaseTenantAdmin(admin.ModelAdmin):
    """
    Admin base que filtra automáticamente por tenant.
    
    Comportamiento:
    - SuperAdmin: Ve todos los registros
    - Usuario con tenant: Ve solo su tenant
    - Usuario sin tenant: No ve nada
    
    Uso:
        @admin.register(MyModel)
        class MyModelAdmin(BaseTenantAdmin):
            list_display = ['field1', 'field2']
    """
    
    tenant_lookup = "tenant"
    tenant_object_paths = (
        "tenant",
        "user.tenant",
        "product.tenant",
        "branch.tenant",
        "employee.tenant",
        "period.employee.tenant",
        "invoice.user.tenant",
        "sale.tenant",
        "subscription.user.tenant",
    )
    remove_delete_selected = True

    def _get_user_tenant(self, request):
        if not hasattr(request.user, "tenant"):
            return None
        return request.user.tenant

    def _resolve_obj_tenant(self, obj):
        for path in self.tenant_object_paths:
            current = obj
            try:
                for attr in path.split("."):
                    current = getattr(current, attr)
            except AttributeError:
                continue
            if current is not None:
                return current
        return None

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        # SuperAdmin ve todo
        if request.user.is_superuser:
            return qs
        
        # Usuario sin tenant no ve nada
        user_tenant = self._get_user_tenant(request)
        if not user_tenant:
            return qs.none()
        
        try:
            return qs.filter(**{self.tenant_lookup: user_tenant})
        except FieldError:
            return qs.none()
    
    def has_add_permission(self, request):
        """Solo usuarios con tenant pueden agregar"""
        if not super().has_add_permission(request):
            return False
        if request.user.is_superuser:
            return True
        return self._get_user_tenant(request) is not None

    def has_module_permission(self, request):
        if not super().has_module_permission(request):
            return False
        if request.user.is_superuser:
            return True
        return self._get_user_tenant(request) is not None

    def has_view_permission(self, request, obj=None):
        if not super().has_view_permission(request, obj):
            return False

        if request.user.is_superuser:
            return True

        user_tenant = self._get_user_tenant(request)
        if user_tenant is None:
            return False

        if obj is None:
            return True

        obj_tenant = self._resolve_obj_tenant(obj)
        return obj_tenant == user_tenant
    
    def has_change_permission(self, request, obj=None):
        """Validar que el objeto pertenece al tenant del usuario"""
        if not super().has_change_permission(request, obj):
            return False

        if request.user.is_superuser:
            return True

        user_tenant = self._get_user_tenant(request)
        if user_tenant is None:
            return False

        if obj is None:
            return True

        obj_tenant = self._resolve_obj_tenant(obj)
        return obj_tenant == user_tenant
    
    def has_delete_permission(self, request, obj=None):
        """Validar que el objeto pertenece al tenant del usuario"""
        if not super().has_delete_permission(request, obj):
            return False

        if request.user.is_superuser:
            return True

        user_tenant = self._get_user_tenant(request)
        if user_tenant is None:
            return False

        if obj is None:
            return True

        obj_tenant = self._resolve_obj_tenant(obj)
        return obj_tenant == user_tenant
    
    def save_model(self, request, obj, form, change):
        """Asignar tenant automáticamente para usuarios no superadmin."""
        if not request.user.is_superuser and hasattr(obj, "tenant_id"):
            obj.tenant = self._get_user_tenant(request)
        super().save_model(request, obj, form, change)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if self.remove_delete_selected:
            actions.pop("delete_selected", None)
        return actions


class BaseTenantTabularInline(admin.TabularInline):
    """Inline base con filtrado por tenant"""
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        if not hasattr(request.user, 'tenant') or not request.user.tenant:
            return qs.none()
        
        if hasattr(qs.model, 'tenant'):
            return qs.filter(tenant=request.user.tenant)
        
        return qs


class BaseTenantStackedInline(admin.StackedInline):
    """Inline base con filtrado por tenant"""
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        if not hasattr(request.user, 'tenant') or not request.user.tenant:
            return qs.none()
        
        if hasattr(qs.model, 'tenant'):
            return qs.filter(tenant=request.user.tenant)
        
        return qs
