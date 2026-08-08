from django.contrib import admin
from apps.tenants_api.base_admin import BaseTenantAdmin
from .models import Sale, SaleDetail, CashRegister


@admin.register(Sale)
class SaleAdmin(BaseTenantAdmin):
    list_display = ['id', 'tenant', 'employee', 'client', 'total', 'status', 'date_time']
    list_filter = ['status', 'date_time']
    search_fields = ['id', 'client__name', 'employee__user__email']
    readonly_fields = ['created_at', 'updated_at', 'tenant', 'user', 'total', 'discount', 'paid']


@admin.register(CashRegister)
class CashRegisterAdmin(BaseTenantAdmin):
    tenant_lookup = "user__tenant"
    list_display = ['id', 'user', 'opened_at', 'closed_at', 'is_open']
    list_filter = ['is_open', 'opened_at']
    readonly_fields = ['opened_at', 'closed_at']
