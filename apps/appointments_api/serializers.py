from django.utils import timezone
from rest_framework import serializers
from .models import Appointment
from apps.clients_api.models import Client
from apps.roles_api.models import Role


class AppointmentSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())
    stylist = serializers.PrimaryKeyRelatedField(queryset=Role.objects.filter(name='stylist'))
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all())

    class Meta:
        model = Appointment
        fields = [
            'id',
            'client',
            'stylist',
            'role',
            'status',
            'created_at',
            'description',
            'updated_at',
            'date_time'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_date_time(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Cannot schedule appointments in the past.")
        return value