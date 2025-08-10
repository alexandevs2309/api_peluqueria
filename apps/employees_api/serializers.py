from rest_framework import serializers

from apps.services_api.models import Service
from .models import Employee, EmployeeService, WorkSchedule
from apps.services_api.serializers import ServiceSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class EmployeeSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='user', write_only=True)
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Employee
        fields = ['id', 'user', 'user_id', 'specialty', 'phone', 'hire_date', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        user = validated_data.pop('user')
        employee = Employee.objects.create(user=user, **validated_data)
        return employee

class EmployeeServiceSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all(), source='service', write_only=True)

    class Meta:
        model = EmployeeService
        fields = ['id', 'employee', 'service', 'service_id', 'created_at']
        read_only_fields = ['created_at']

class WorkScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkSchedule
        fields = ['id', 'employee', 'day_of_week', 'start_time', 'end_time', 'created_at']
        read_only_fields = ['created_at']