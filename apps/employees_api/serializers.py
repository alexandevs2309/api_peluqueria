from rest_framework import serializers

from apps.services_api.models import Service
from .models import Employee, EmployeeService, WorkSchedule
from apps.services_api.serializers import ServiceSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class UserBasicSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'first_name', 'last_name', 'role']
    
    def get_first_name(self, obj):
        if obj.full_name:
            parts = obj.full_name.split(' ', 1)
            return parts[0] if parts else ''
        return ''
    
    def get_last_name(self, obj):
        if obj.full_name:
            parts = obj.full_name.split(' ', 1)
            return parts[1] if len(parts) > 1 else ''
        return ''

class EmployeeSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source='user', write_only=True)
    user = UserBasicSerializer(read_only=True)
    user_id_read = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = Employee
        fields = ['id', 'user', 'user_id', 'user_id_read', 'specialty', 'phone', 'hire_date', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Asegurar que el usuario tenga la información completa
        if instance.user:
            full_name_parts = instance.user.full_name.split(' ', 1) if instance.user.full_name else ['', '']
            first_name = full_name_parts[0] if full_name_parts else ''
            last_name = full_name_parts[1] if len(full_name_parts) > 1 else ''
            
            data['user'] = {
                'id': instance.user.id,
                'email': instance.user.email,
                'full_name': instance.user.full_name or '',
                'first_name': first_name,
                'last_name': last_name,
                'role': instance.user.role or 'Sin rol'
            }
        return data

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