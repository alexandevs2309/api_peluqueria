import json

from rest_framework import serializers
from .models import Service, ServiceCategory
from apps.roles_api.models import Role


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ServiceCategoryIdsField(serializers.ListField):
    child = serializers.IntegerField()

    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                self.fail('invalid')
        elif isinstance(data, list) and len(data) == 1 and isinstance(data[0], str) and data[0].startswith('['):
            try:
                data = json.loads(data[0])
            except json.JSONDecodeError:
                pass
        if isinstance(data, list):
            data = [x for x in data if x != '']
        return super().to_internal_value(data)

    def to_representation(self, data):
        if hasattr(data, 'all'):
            data = data.all()
        return [item.pk for item in data]


class ServiceSerializer(serializers.ModelSerializer):
    allowed_roles = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        many=True,
        required=False,
        allow_empty=True,
        allow_null=True
    )
    categories = ServiceCategoryIdsField(required=False)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'image', 'image_url', 'categories', 'price', 'duration', 'is_active', 'allowed_roles', 'created_at', 'updated_at']
        read_only_fields = ['id', 'image_url', 'created_at', 'updated_at']

    def create(self, validated_data):
        categories = validated_data.pop('categories', None)
        instance = super().create(validated_data)
        if categories is not None:
            instance.categories.set(categories)
        return instance

    def update(self, instance, validated_data):
        categories = validated_data.pop('categories', None)
        instance = super().update(instance, validated_data)
        if categories is not None:
            instance.categories.set(categories)
        return instance

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def validate_categories(self, value):
        if not value:
            return value
        existing = set(ServiceCategory.objects.filter(id__in=value).values_list('id', flat=True))
        missing = set(value) - existing
        if missing:
            raise serializers.ValidationError(f"Categorías no encontradas: {missing}")
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.image:
            request = self.context.get('request')
            if request:
                data['image'] = request.build_absolute_uri(instance.image.url)
            else:
                data['image'] = instance.image.url
        else:
            data['image'] = None
        return data