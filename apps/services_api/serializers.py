import json
import logging

from django.db import IntegrityError
from rest_framework import serializers
from .models import Service, ServiceCategory
from apps.roles_api.models import Role

logger = logging.getLogger(__name__)


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
        queryset=lambda: Role.objects.all(),
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

    def validate_name(self, value):
        request = self.context.get('request')
        if request and hasattr(request, 'tenant') and request.tenant:
            qs = Service.objects.filter(name__iexact=value, tenant=request.tenant)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    f"Ya existe un servicio con el nombre '{value}' en este establecimiento."
                )
        return value

    def create(self, validated_data):
        categories = validated_data.pop('categories', None)
        image_file = validated_data.pop('image', None)
        try:
            instance = super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                "Error de concurrencia: ya existe un servicio con ese nombre. Intenta de nuevo."
            )
        if categories is not None:
            instance.categories.set(categories)
        if image_file:
            self._save_image(instance, image_file)
        return instance

    def update(self, instance, validated_data):
        categories = validated_data.pop('categories', None)
        image_file = validated_data.pop('image', None)
        logger.debug("ServiceSerializer.update — validated_data keys: %s, has_image: %s, has_categories: %s",
                      validated_data.keys(), bool(image_file), categories is not None)
        try:
            instance = super().update(instance, validated_data)
        except Exception as e:
            logger.error("ServiceSerializer.update — super().update failed: %s", e, exc_info=True)
            raise
        if categories is not None:
            instance.categories.set(categories)
        if image_file:
            self._save_image(instance, image_file)
        return instance

    def _save_image(self, instance, image_file):
        try:
            instance.image = image_file
            instance.save(update_fields=['image'])
        except Exception as e:
            logger.warning("No se pudo guardar la imagen del servicio %s: %s", instance.id, e)

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
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None) if request else None
        qs = ServiceCategory.objects.filter(id__in=value)
        if tenant:
            qs = qs.filter(tenant=tenant)
        existing = set(qs.values_list('id', flat=True))
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