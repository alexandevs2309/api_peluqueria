from rest_framework import serializers

from apps.services_api.models import Service
from .models import Employee, EmployeeService, WorkSchedule, AttendanceRecord
from apps.services_api.serializers import ServiceSerializer
from django.contrib.auth import get_user_model
from apps.auth_api.role_utils import get_effective_role_api

User = get_user_model()

class UserBasicSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'first_name', 'last_name', 'role']

    def get_role(self, obj):
        return get_effective_role_api(obj, tenant=getattr(obj, 'tenant', None))
    
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
    service_ids = serializers.SerializerMethodField()
    services_count = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ['id', 'user', 'user_id', 'user_id_read', 'specialty', 'phone', 'hire_date', 'is_active', 'service_ids', 'services_count', 'created_at', 'updated_at']
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
                'role': get_effective_role_api(instance.user, tenant=getattr(instance.user, 'tenant', None)) or 'Sin rol'
            }
        return data

    def create(self, validated_data):
        user = validated_data.pop('user')
        employee = Employee.objects.create(user=user, **validated_data)
        return employee

    def get_service_ids(self, obj):
        return [employee_service.service_id for employee_service in obj.services.all()]

    def get_services_count(self, obj):
        return len(obj.services.all())

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


class AttendanceRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            'id',
            'employee',
            'employee_name',
            'work_date',
            'check_in_at',
            'check_out_at',
            'status',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_employee_name(self, obj):
        if obj.employee and obj.employee.user:
            return obj.employee.user.full_name or obj.employee.user.email
        return ''
