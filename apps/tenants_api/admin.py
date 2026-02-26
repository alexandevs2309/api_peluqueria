from django.contrib import admin
from apps.tenants_api.base_admin import BaseTenantAdmin
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
