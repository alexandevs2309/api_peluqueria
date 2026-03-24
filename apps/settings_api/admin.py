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
            'fields': (
                'stripe_enabled', 'paypal_enabled', 'twilio_enabled', 'sendgrid_enabled', 'aws_s3_enabled',
                'stripe_public_key', 'stripe_secret_key', 'webhook_secret',
                'paypal_client_id', 'paypal_client_secret', 'paypal_sandbox',
                'twilio_account_sid', 'twilio_auth_token', 'twilio_phone_number',
                'smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'from_email', 'from_name'
            )
        }),
        ('System', {
            'fields': ('maintenance_mode', 'email_notifications', 'auto_suspend_expired', 'auto_upgrade_limits')
        }),
        ('Security', {
            'fields': ('jwt_expiry_minutes', 'max_login_attempts', 'password_min_length', 'require_email_verification', 'enable_mfa')
        })
    )

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions
