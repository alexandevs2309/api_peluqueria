from django.utils import timezone
from rest_framework import serializers
from .models import Appointment
from apps.clients_api.models import Client
from apps.services_api.models import Service, StylistService
from apps.roles_api.models import Role
from django.contrib.auth import get_user_model
from apps.employees_api.models import Employee, WorkSchedule
from apps.employees_api.serializers import EmployeeSerializer

User = get_user_model()

class AppointmentSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())
    stylist = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    stylist_info = EmployeeSerializer(source='stylist.employee_profile', read_only=True)
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), required=False, allow_null=True)
    date_time = serializers.DateTimeField(default=timezone.now)
    service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
        allow_null=True,
        required=False
    )
    sale = serializers.PrimaryKeyRelatedField(read_only=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Temporalmente sin filtros para debuggear
        pass

    class Meta:
        model = Appointment
        fields = [
            'id', 'client', 'stylist', 'role', 'service', 'stylist_info',
            'status', 'created_at', 'description', 'updated_at', 'date_time' ,'sale'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {'stylist_info': {'read_only': True}}  # Añadir como read_only

    def validate(self, data):
        # Temporalmente sin validaciones complejas
        return data

    def validate_date_time(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("La fecha y hora de la cita no puede ser en el pasado.")
        return value