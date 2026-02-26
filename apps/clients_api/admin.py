from django.contrib import admin
from .models import Client


class TenantFilteredAdmin(admin.ModelAdmin):
    """Base admin que filtra por tenant automáticamente"""
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'tenant') and request.user.tenant:
            return qs.filter(tenant=request.user.tenant)
        return qs.none()


@admin.register(Client)
class ClientAdmin(TenantFilteredAdmin):
    list_display = ['id', 'full_name', 'email', 'phone', 'tenant', 'created_at']
    list_filter = ['created_at']
    search_fields = ['full_name', 'email', 'phone']
