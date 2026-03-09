from django.contrib import admin
from apps.tenants_api.base_admin import BaseTenantAdmin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(BaseTenantAdmin):
    tenant_lookup = 'user__tenant'
    list_display = ('timestamp', 'user', 'action', 'source', 'object_id')  # <-- no usamos model_name
    list_filter = ('action', 'source', 'user')
    search_fields = ('user__username', 'description', 'object_id')
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp', 'user', 'action', 'description', 'content_type', 'object_id', 'ip_address', 'user_agent', 'extra_data', 'source')

    def has_add_permission(self, request):
        return False
