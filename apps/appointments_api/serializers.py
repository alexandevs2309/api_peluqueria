from django.utils import timezone
from rest_framework import serializers
from .models import Appointment
from apps.clients_api.models import Client
from apps.services_api.models import Service, StylistService
from apps.roles_api.models import Role
from django.contrib.auth import get_user_model

User = get_user_model()

class AppointmentSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())
    stylist = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())  # Cambiado a User
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), required=False, allow_null=True)
    service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
        allow_null=True,
        required=False
    )

    class Meta:
        model = Appointment
        fields = [
            'id',
            'client',
            'stylist',
            'role',
            'service',
            'status',
            'created_at',
            'description',
            'updated_at',
            'date_time'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        if data.get('service') and data.get('stylist'):
            if not StylistService.objects.filter(
                service=data['service'],
                stylist=data['stylist']  # Compatible con User
            ).exists():
                raise serializers.ValidationError(
                    "El estilista no ofrece este servicio."
                )
        return data

    def validate_date_time(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("La fecha y hora de la cita no puede ser en el pasado.")
        return value