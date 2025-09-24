from django.contrib import admin
from .models import Tenant

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "subdomain", "owner", "subscription_plan", "subscription_status", "is_active", "created_at")
    list_filter = ("subscription_plan", "subscription_status", "is_active")
    search_fields = ("name", "subdomain", "owner__username")
    fields = ("name", "subdomain", "owner", "subscription_plan", "subscription_status", "trial_end_date", "max_employees", "max_users", "is_active")
