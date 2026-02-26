"""
Base Admin classes para filtrado automático por tenant.
Mantiene compatibilidad con comportamiento actual.
"""
from django.contrib import admin


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
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        
        # SuperAdmin ve todo
        if request.user.is_superuser:
            return qs
        
        # Usuario sin tenant no ve nada
        if not hasattr(request.user, 'tenant') or not request.user.tenant:
            return qs.none()
        
        # Filtrar por tenant del usuario
        if hasattr(qs.model, 'tenant'):
            return qs.filter(tenant=request.user.tenant)
        
        # Si el modelo no tiene tenant, retornar vacío por seguridad
        return qs.none()
    
    def has_add_permission(self, request):
        """Solo usuarios con tenant pueden agregar"""
        if request.user.is_superuser:
            return True
        return hasattr(request.user, 'tenant') and request.user.tenant is not None
    
    def has_change_permission(self, request, obj=None):
        """Validar que el objeto pertenece al tenant del usuario"""
        if request.user.is_superuser:
            return True
        
        if obj is None:
            return True
        
        if hasattr(obj, 'tenant') and hasattr(request.user, 'tenant'):
            return obj.tenant == request.user.tenant
        
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Validar que el objeto pertenece al tenant del usuario"""
        if request.user.is_superuser:
            return True
        
        if obj is None:
            return True
        
        if hasattr(obj, 'tenant') and hasattr(request.user, 'tenant'):
            return obj.tenant == request.user.tenant
        
        return False
    
    def save_model(self, request, obj, form, change):
        """Asignar tenant automáticamente al crear"""
        if not change and hasattr(obj, 'tenant') and not obj.tenant:
            if not request.user.is_superuser:
                obj.tenant = request.user.tenant
        super().save_model(request, obj, form, change)


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
