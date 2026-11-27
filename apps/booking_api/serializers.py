from rest_framework import serializers
from apps.services_api.models import Service
from apps.utils.booking_urls import public_booking_url
from apps.employees_api.models import Employee, WorkSchedule
from apps.clients_api.models import Client
from django.contrib.auth import get_user_model
from datetime import date, datetime, timedelta, time

User = get_user_model()


class PublicTenantInfoSerializer(serializers.Serializer):
    name = serializers.CharField(source='tenant.name')
    subdomain = serializers.CharField(source='tenant.subdomain')
    booking_url = serializers.SerializerMethodField()
    # El correo de contacto del negocio también es su identidad de acceso: no se
    # expone en el portal público de reservas. Sí se muestra el teléfono público.
    contact_phone = serializers.CharField(source='tenant.contact_phone', allow_null=True)
    address = serializers.CharField(source='tenant.address', allow_null=True)
    locale = serializers.CharField(source='tenant.locale')
    currency = serializers.CharField(source='tenant.currency')
    time_zone = serializers.CharField(source='tenant.time_zone')

    def get_booking_url(self, obj):
        """Enlace canónico del negocio, derivado de su subdomain y de FRONTEND_URL."""
        tenant = obj.get('tenant') if isinstance(obj, dict) else obj
        return public_booking_url(tenant)


class PublicServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'price', 'description', 'duration', 'image']


class PublicStylistSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.SerializerMethodField()
    profession = serializers.CharField()
    profession_display = serializers.SerializerMethodField()
    avatar = serializers.ImageField(allow_null=True)

    def get_full_name(self, obj):
        if obj.user and obj.user.full_name:
            return obj.user.full_name
        return obj.user.email if obj.user else 'Sin nombre'

    def get_profession_display(self, obj):
        profession_map = dict(Employee.PROFESSION_CHOICES)
        return profession_map.get(obj.profession, obj.profession or '')


class PublicBookingSerializer(serializers.Serializer):
    stylist_id = serializers.IntegerField()
    service_id = serializers.IntegerField()
    date = serializers.DateField()
    time = serializers.TimeField()
    client_name = serializers.CharField(max_length=255)
    client_email = serializers.EmailField(required=False, allow_blank=True)
    client_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_date(self, value):
        if value < date.today():
            raise serializers.ValidationError('La fecha no puede ser en el pasado')
        return value

    def validate(self, attrs):
        if not attrs.get('client_email') and not attrs.get('client_phone'):
            raise serializers.ValidationError(
                'Debe proporcionar al menos un email o teléfono de contacto'
            )
        return attrs
