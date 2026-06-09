from django.contrib import admin
from .models import NotificationTemplate, Notification, NotificationPreference, NotificationLog, InAppNotification


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'notification_type', 'is_active', 'tenant', 'created_at']
    list_filter = ['type', 'notification_type', 'is_active', 'tenant']
    search_fields = ['name', 'subject', 'body']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        ('Información básica', {
            'fields': ['name', 'type', 'notification_type', 'is_active', 'tenant']
        }),
        ('Contenido', {
            'fields': ['subject', 'body', 'available_variables']
        }),
        ('Metadatos', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'recipient', 'template', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['recipient__email', 'subject', 'message']
    readonly_fields = ['created_at', 'sent_at']


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_enabled', 'sms_enabled', 'whatsapp_enabled', 'push_enabled']
    list_filter = ['email_enabled', 'sms_enabled', 'whatsapp_enabled', 'push_enabled']
    search_fields = ['user__email', 'user__full_name']


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'notification', 'channel', 'provider', 'status', 'created_at']
    list_filter = ['channel', 'provider', 'status', 'created_at']
    search_fields = ['notification__subject', 'error_message']
    readonly_fields = ['created_at']


@admin.register(InAppNotification)
class InAppNotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'recipient', 'type', 'title', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['recipient__email', 'title', 'message']
    readonly_fields = ['created_at']
