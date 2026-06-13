from rest_framework import serializers
from apps.services_api.models import Service
from apps.employees_api.models import Employee, WorkSchedule
from apps.clients_api.models import Client
from django.contrib.auth import get_user_model
from datetime import date, datetime, timedelta, time

User = get_user_model()


class PublicTenantInfoSerializer(serializers.Serializer):
    name = serializers.CharField(source='tenant.name')
    subdomain = serializers.CharField(source='tenant.subdomain')
    contact_email = serializers.EmailField(source='tenant.contact_email', allow_null=True)
    contact_phone = serializers.CharField(source='tenant.contact_phone', allow_null=True)
    address = serializers.CharField(source='tenant.address', allow_null=True)
    locale = serializers.CharField(source='tenant.locale')
    currency = serializers.CharField(source='tenant.currency')
    time_zone = serializers.CharField(source='tenant.time_zone')


class PublicServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'price', 'description', 'duration', 'image']


class PublicStylistSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.SerializerMethodField()
    specialty = serializers.CharField()
    avatar = serializers.ImageField(allow_null=True)

    def get_full_name(self, obj):
        if obj.user and obj.user.full_name:
            return obj.user.full_name
        return obj.user.email if obj.user else 'Sin nombre'


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
