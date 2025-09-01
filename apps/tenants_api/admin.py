from django.contrib import admin
from .models import Tenant

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "subdomain", "owner", "plan_type", "subscription_status", "is_active", "created_at")
    list_filter = ("plan_type", "subscription_status", "is_active")
    search_fields = ("name", "subdomain", "owner__username")
