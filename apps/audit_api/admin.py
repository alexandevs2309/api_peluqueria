from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'source', 'object_id')  # <-- no usamos model_name
    list_filter = ('action', 'source', 'user')
    search_fields = ('user__username', 'description', 'object_id')
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp',)  # los logs no deberían modificarse
