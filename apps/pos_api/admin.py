from django.contrib import admin
from .models import Sale, SaleDetail, CashRegister


class TenantFilteredAdmin(admin.ModelAdmin):
    """Base admin que filtra por tenant automáticamente"""
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'tenant') and request.user.tenant:
            return qs.filter(tenant=request.user.tenant)
        return qs.none()


@admin.register(Sale)
class SaleAdmin(TenantFilteredAdmin):
    list_display = ['id', 'tenant', 'employee', 'client', 'total', 'status', 'date_time']
    list_filter = ['status', 'date_time']
    search_fields = ['id', 'client__name', 'employee__user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CashRegister)
class CashRegisterAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'opened_at', 'closed_at', 'is_open']
    list_filter = ['is_open', 'opened_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user__tenant=request.user.tenant)
