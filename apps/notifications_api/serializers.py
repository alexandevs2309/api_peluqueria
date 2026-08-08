from rest_framework import serializers
from .models import Notification, NotificationTemplate, NotificationPreference, NotificationLog, InAppNotification

class InAppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotification
        fields = ['id', 'type', 'title', 'message', 'is_read', 'created_at']
        read_only_fields = ['created_at']

class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = ['id', 'tenant', 'name', 'type', 'notification_type', 'subject', 'body', 'is_html', 'is_active', 'available_variables']
        read_only_fields = ['tenant']

class NotificationSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_type = serializers.CharField(source='template.type', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'template', 'template_name', 'template_type',
            'subject', 'message', 'status', 'priority', 'scheduled_at',
            'sent_at', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['sent_at', 'created_at', 'updated_at']

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['id', 'email_enabled', 'sms_enabled', 'push_enabled', 'whatsapp_enabled',
                  'appointment_reminders', 'payment_notifications',
                  'earnings_notifications', 'system_notifications',
                  'marketing_notifications', 'quiet_hours_start', 'quiet_hours_end',
                  'timezone']

    def validate_whatsapp_enabled(self, value):
        if not value:
            return value
        request = self.context.get('request')
        if request and not request.user.is_superuser:
            from apps.subscriptions_api.permissions import tenant_has_feature
            tenant = getattr(request, 'tenant', getattr(request.user, 'tenant', None))
            if not tenant or not tenant_has_feature(tenant, 'whatsapp_notifications'):
                raise serializers.ValidationError('Tu plan no incluye notificaciones por WhatsApp. Actualiza a Enterprise.')
        return value

class NotificationLogSerializer(serializers.ModelSerializer):
    notification_subject = serializers.CharField(source='notification.subject', read_only=True)

    class Meta:
        model = NotificationLog
        fields = [
            'id', 'notification', 'notification_subject', 'channel',
            'provider', 'status', 'response_data', 'error_message', 'created_at'
        ]
