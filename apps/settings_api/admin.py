from django.contrib import admin
from .models import SystemSettings

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ['platform_name', 'max_tenants', 'trial_days', 'maintenance_mode', 'updated_at']
    fieldsets = (
        ('General', {
            'fields': ('platform_name', 'support_email', 'max_tenants', 'trial_days', 'default_currency')
        }),
        ('Platform', {
            'fields': ('platform_domain', 'supported_languages', 'platform_commission_rate')
        }),
        ('Plan Limits', {
            'fields': ('basic_plan_max_employees', 'premium_plan_max_employees', 'enterprise_plan_max_employees')
        }),
        ('Integrations', {
            'fields': ('stripe_enabled', 'paypal_enabled', 'twilio_enabled', 'sendgrid_enabled', 'aws_s3_enabled')
        }),
        ('System', {
            'fields': ('maintenance_mode', 'email_notifications', 'auto_suspend_expired')
        })
    )