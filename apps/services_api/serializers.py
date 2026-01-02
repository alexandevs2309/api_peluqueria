from rest_framework import serializers
from .models import Service, ServiceCategory
from apps.roles_api.models import Role

class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'description', 'is_active']

class ServiceSerializer(serializers.ModelSerializer):
    allowed_roles = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        many=True,
        required=False,
        allow_empty=True,
        allow_null=True
    )
    categories = serializers.PrimaryKeyRelatedField(
        queryset=ServiceCategory.objects.filter(is_active=True),
        many=True,
        required=False,
        allow_empty=True
    )
    category_names = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'category', 'categories', 'category_names', 'price', 'duration', 'is_active', 'allowed_roles', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'category_names']

    def get_category_names(self, obj):
        return [cat.name for cat in obj.categories.all()]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return value