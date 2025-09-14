from django.contrib import admin
from .models import PaymentProvider, Payment, WebhookEvent

@admin.register(PaymentProvider)
class PaymentProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'amount', 'status', 'provider', 'created_at']
    list_filter = ['status', 'provider', 'created_at']
    search_fields = ['user__email', 'provider_payment_id']
    readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ['event_id', 'provider', 'event_type', 'processed', 'created_at']
    list_filter = ['provider', 'processed', 'event_type']
    readonly_fields = ['created_at']