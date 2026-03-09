from django.contrib import admin
from apps.tenants_api.base_admin import BaseTenantAdmin
from .models import SubscriptionPlan, UserSubscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_month', 'stripe_price_id', 'is_active')
    search_fields = ('name', 'stripe_price_id')
    list_filter = ('is_active',)
    fields = (
        'name', 'description', 'price', 'duration_month', 'stripe_price_id',
        'max_employees', 'max_users', 'allows_multiple_branches', 'features', 'is_active'
    )

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(UserSubscription)
class UserSubscriptionAdmin(BaseTenantAdmin):
    tenant_lookup = "user__tenant"
    list_display = ('user', 'plan', 'is_active', 'start_date', 'end_date')
    readonly_fields = ('user', 'plan', 'start_date', 'end_date', 'created_at')
