from rest_framework import serializers
from .models import Notification, NotificationTemplate, NotificationPreference, NotificationLog

class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = '__all__'

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
        fields = '__all__'

class NotificationLogSerializer(serializers.ModelSerializer):
    notification_subject = serializers.CharField(source='notification.subject', read_only=True)

    class Meta:
        model = NotificationLog
        fields = [
            'id', 'notification', 'notification_subject', 'channel',
            'provider', 'status', 'response_data', 'error_message', 'created_at'
        ]
