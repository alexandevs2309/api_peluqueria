from rest_framework import serializers
from .models import Service, ServiceCategory
from apps.roles_api.models import Role

class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ServiceSerializer(serializers.ModelSerializer):
    allowed_roles = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        many=True,
        required=False,
        allow_empty=True,
        allow_null=True
    )
    categories = serializers.PrimaryKeyRelatedField(
        queryset=ServiceCategory.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'categories', 'price', 'duration', 'is_active', 'allowed_roles', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return value