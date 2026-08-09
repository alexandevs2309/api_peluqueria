from rest_framework import serializers

from apps.services_api.models import Service, ServiceEmployee
from .models import Employee, WorkSchedule, AttendanceRecord
from apps.services_api.serializers import ServiceSerializer
from django.contrib.auth import get_user_model
from apps.auth_api.role_utils import get_effective_role_api
from apps.settings_api.models import Branch

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
    user_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    user = UserBasicSerializer(read_only=True)
    user_id_read = serializers.IntegerField(source='user.id', read_only=True)
    service_ids = serializers.SerializerMethodField()
    services_count = serializers.SerializerMethodField()
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all(), required=False, allow_null=True)
    profession = serializers.CharField(required=False, allow_blank=True)
    profession_display = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            'id', 'branch', 'user', 'user_id', 'user_id_read',
            'profession', 'profession_display', 'payment_type', 'fixed_salary', 'commission_rate', 'payment_type', 'fixed_salary', 'commission_rate',
            'phone', 'hire_date', 'is_active',
            'service_ids', 'services_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            tenant = getattr(request, 'tenant', None)
            if tenant:
                self.fields['branch'].queryset = Branch.objects.filter(tenant=tenant)
            else:
                self.fields['branch'].queryset = Branch.objects.none()
    
    def validate(self, attrs):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None) if request else None
        if not tenant and request and getattr(request, 'user', None) and getattr(request.user, 'tenant', None):
            tenant = request.user.tenant

        # Si se está actualizando un empleado existente (PUT o PATCH), mantener su usuario asignado
        if self.instance:
            if not attrs.get('user'):
                attrs['user'] = self.instance.user
            return super().validate(attrs)

        user_id = attrs.pop('user_id', None) or self.initial_data.get('user_id')

        if user_id:
            try:
                user_obj = User.objects.get(id=user_id)
                if tenant and user_obj.tenant_id != tenant.id:
                    raise serializers.ValidationError({"user_id": ["El usuario seleccionado no pertenece a este negocio."]})
                attrs['user'] = user_obj
            except User.DoesNotExist:
                raise serializers.ValidationError({"user_id": ["Usuario no encontrado."]})
        elif 'user' not in attrs:
            user_data = self.initial_data.get('user')
            if isinstance(user_data, dict) and user_data.get('email'):
                email = user_data['email'].strip().lower()
                full_name = user_data.get('full_name', '').strip()
                password = user_data.get('password') or 'Auron123!'
                
                user_obj = User.objects.filter(email=email, tenant=tenant).first() if tenant else User.objects.filter(email=email).first()
                if user_obj:
                    if Employee.objects.filter(user=user_obj).exists():
                        raise serializers.ValidationError({"email": ["Ya existe un empleado registrado con este correo electrónico."]})
                    else:
                        if getattr(user_obj, 'role', '') != 'CLIENT_STAFF':
                            user_obj.role = 'CLIENT_STAFF'
                            user_obj.save(update_fields=['role'])
                else:
                    try:
                        user_obj = User.objects.create_user(
                            email=email,
                            password=password,
                            full_name=full_name,
                            tenant=tenant,
                            role='CLIENT_STAFF'
                        )
                    except Exception as exc:
                        raise serializers.ValidationError({"user": [f"Error al crear la cuenta del usuario: {str(exc)}"]})
                attrs['user'] = user_obj
            else:
                raise serializers.ValidationError({"user": ["Debe proporcionar el correo electrónico del empleado."]})
                
        return super().validate(attrs)

    def validate_user_id(self, value):
        request = self.context.get('request')
        if request:
            tenant = getattr(request, 'tenant', None)
            if tenant and value.tenant_id != tenant.id:
                raise serializers.ValidationError("El usuario seleccionado no pertenece a este negocio")
        return value
    
    def validate_branch(self, value):
        if value:
            request = self.context.get('request')
            if request and not request.user.is_superuser:
                tenant = getattr(request, 'tenant', None)
                if tenant and value.tenant_id != tenant.id:
                    raise serializers.ValidationError("La sucursal seleccionada no pertenece a este negocio")
        return value

    def get_profession_display(self, obj):
        """Devuelve la etiqueta legible de la profesión para mostrar en UI."""
        if not obj.profession:
            return ''
        profession_map = dict(Employee.PROFESSION_CHOICES)
        return profession_map.get(obj.profession, obj.profession)

    def to_representation(self, instance):
        data = super().to_representation(instance)
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
        profession = validated_data.pop('profession', None)
        if not profession:
            profession = 'barber'
        else:
            profession = profession.lower()
        validated_data['profession'] = profession
        
        employee = Employee.objects.create(**validated_data)
        
        # Sync business_role on user
        if employee.user:
            role_map = {
                'receptionist': 'frontdesk_cashier',
                'manager': 'manager',
                'owner': 'owner'
            }
            business_role = role_map.get(profession, 'professional')
            employee.user.business_role = business_role
            employee.user.save(update_fields=['business_role'])
            
        return employee

    def update(self, instance, validated_data):
        if 'profession' in validated_data:
            instance.profession = validated_data['profession'].lower()
            # Sync business_role on user
            if instance.user:
                role_map = {
                    'receptionist': 'frontdesk_cashier',
                    'manager': 'manager',
                    'owner': 'owner'
                }
                business_role = role_map.get(instance.profession, 'professional')
                instance.user.business_role = business_role
                instance.user.save(update_fields=['business_role'])
                
        for field in ['phone', 'hire_date', 'is_active', 'branch']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()
        return instance

    def get_service_ids(self, obj):
        return [se.service_id for se in obj.employee_services.all()]

    def get_services_count(self, obj):
        return obj.employee_services.count()


class EmployeeServiceSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    service_id = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all(), source='service', write_only=True)

    class Meta:
        model = ServiceEmployee
        fields = ['id', 'employee', 'service', 'service_id', 'created_at']
        read_only_fields = ['created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            tenant = getattr(request, 'tenant', None)
            if tenant:
                self.fields['employee'].queryset = Employee.objects.filter(user__tenant=tenant)
                self.fields['service_id'].queryset = Service.objects.filter(tenant=tenant)

class WorkScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkSchedule
        fields = ['id', 'employee', 'day_of_week', 'start_time', 'end_time', 'created_at']
        read_only_fields = ['created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            tenant = getattr(request, 'tenant', None)
            if tenant:
                self.fields['employee'].queryset = Employee.objects.filter(user__tenant=tenant)


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
            'is_justified',
            'justification_reason',
            'justified_by',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'justified_by']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            tenant = getattr(request, 'tenant', None)
            if tenant:
                self.fields['employee'].queryset = Employee.objects.filter(user__tenant=tenant)
                if 'justified_by' in self.fields:
                    self.fields['justified_by'].queryset = User.objects.filter(tenant=tenant)

    def get_employee_name(self, obj):
        if obj.employee and obj.employee.user:
            return obj.employee.user.full_name or obj.employee.user.email
        return ''
