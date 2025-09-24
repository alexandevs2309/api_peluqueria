from rest_framework import serializers
from .models import Service
from apps.roles_api.models import Role

class ServiceSerializer(serializers.ModelSerializer):
    allowed_roles = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        many=True,
        required=False,
        allow_empty=True,
        allow_null=True
    )

    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'category', 'price', 'duration', 'is_active', 'allowed_roles', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return value