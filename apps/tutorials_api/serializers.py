from rest_framework import serializers
from .models import Tutorial


class TutorialSerializer(serializers.ModelSerializer):
    module_label = serializers.SerializerMethodField()
    content_type_label = serializers.SerializerMethodField()

    class Meta:
        model = Tutorial
        fields = [
            'id', 'module', 'module_label', 'content_type', 'content_type_label',
            'title', 'description', 'body',
            'video_url', 'thumbnail_url', 'duration', 'order', 'is_published',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_module_label(self, obj):
        return obj.get_module_display()

    def get_content_type_label(self, obj):
        return obj.get_content_type_display()

    def validate(self, attrs):
        content_type = attrs.get('content_type', getattr(self.instance, 'content_type', 'video'))
        video_url = attrs.get('video_url', getattr(self.instance, 'video_url', ''))
        body = attrs.get('body', getattr(self.instance, 'body', ''))
        if content_type == 'video' and not str(video_url or '').strip():
            raise serializers.ValidationError({'video_url': 'La URL del video es requerida para tutoriales de video.'})
        if content_type == 'text' and not str(body or '').strip():
            raise serializers.ValidationError({'body': 'El contenido de texto es requerido para tutoriales de texto.'})
        return attrs
