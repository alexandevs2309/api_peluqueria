from rest_framework import serializers
from .models import Tutorial


class TutorialSerializer(serializers.ModelSerializer):
    module_label = serializers.SerializerMethodField()

    class Meta:
        model = Tutorial
        fields = [
            'id', 'module', 'module_label', 'title', 'description',
            'video_url', 'thumbnail_url', 'duration', 'order', 'is_published',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_module_label(self, obj):
        return obj.get_module_display()
