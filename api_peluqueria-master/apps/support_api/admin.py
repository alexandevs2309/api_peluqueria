from django.contrib import admin
from .models import SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['subject', 'tenant', 'priority', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'priority', 'tenant']
    search_fields = ['subject', 'description', 'created_by__email']
    readonly_fields = ['created_at', 'updated_at']
