from django.contrib import admin
from .models import Tenant

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):  # NO heredar BaseTenantAdmin (es el modelo raíz)
    list_display = ("name", "subdomain", "owner", "subscription_plan", "subscription_status", "is_active", "created_at")
    list_filter = ("subscription_plan", "subscription_status", "is_active")
    search_fields = ("name", "subdomain", "owner__username")
    fields = ("name", "subdomain", "owner", "subscription_plan", "subscription_status", "trial_end_date", "max_employees", "max_users", "is_active")
    
    def get_queryset(self, request):
        """SuperAdmin ve todo, otros usuarios solo su tenant"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'tenant') and request.user.tenant:
            return qs.filter(id=request.user.tenant.id)
        return qs.none()

    def has_add_permission(self, request):
        return request.user.is_superuser and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_delete_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return super().has_change_permission(request, obj)
        if not super().has_change_permission(request, obj):
            return False
        if obj is None:
            return hasattr(request.user, 'tenant') and request.user.tenant is not None
        return hasattr(request.user, 'tenant') and request.user.tenant_id == obj.id

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions
