from django.contrib import admin
from apps.tenants_api.base_admin import BaseTenantAdmin
from .models import PaymentProvider, Payment, WebhookEvent

@admin.register(PaymentProvider)
class PaymentProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

@admin.register(Payment)
class PaymentAdmin(BaseTenantAdmin):
    tenant_lookup = "user__tenant"
    list_display = ['id', 'user', 'amount', 'status', 'provider', 'created_at']
    list_filter = ['status', 'provider', 'created_at']
    search_fields = ['user__email', 'provider_payment_id']
    readonly_fields = [
        'id', 'user', 'subscription', 'provider', 'amount', 'currency', 'status',
        'provider_payment_id', 'provider_customer_id', 'metadata',
        'created_at', 'updated_at', 'completed_at'
    ]

@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ['event_id', 'provider', 'event_type', 'processed', 'created_at']
    list_filter = ['provider', 'processed', 'event_type']
    readonly_fields = ['provider', 'event_id', 'event_type', 'processed', 'data', 'created_at']

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions
