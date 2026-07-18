from django.contrib import admin
from apps.tenants_api.base_admin import BaseTenantAdmin
from .models import Client


@admin.register(Client)
class ClientAdmin(BaseTenantAdmin):
    list_display = ['id', 'full_name', 'email', 'phone', 'tenant', 'created_at']
    list_filter = ['created_at']
    search_fields = ['full_name', 'email', 'phone']
