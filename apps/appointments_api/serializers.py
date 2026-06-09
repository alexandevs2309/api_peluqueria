from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from .models import Appointment
from apps.clients_api.models import Client
from apps.services_api.models import Service
from apps.roles_api.models import Role
from django.contrib.auth import get_user_model
from apps.employees_api.models import Employee, WorkSchedule

User = get_user_model()


class MinimalStylistInfoSerializer(serializers.Serializer):
    """Versión ligera de EmployeeSerializer sin queries adicionales de roles/services."""
    id = serializers.IntegerField()
    specialty = serializers.CharField()
    phone = serializers.CharField()
    is_active = serializers.BooleanField()
    user = serializers.SerializerMethodField()

    def get_user(self, obj):
        if not obj.user:
            return None
        return {
            'id': obj.user.id,
            'email': obj.user.email,
            'full_name': obj.user.full_name or '',
            'first_name': (obj.user.full_name.split(' ', 1)[0] if obj.user.full_name else ''),
            'last_name': (obj.user.full_name.split(' ', 1)[1] if obj.user.full_name and ' ' in obj.user.full_name else ''),
        }


class AppointmentSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())
    stylist = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    stylist_info = MinimalStylistInfoSerializer(source='stylist.employee_profile', read_only=True)
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), required=False, allow_null=True)
    date_time = serializers.DateTimeField(default=timezone.now)
    service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.all(),
        allow_null=True,
        required=False
    )
    sale = serializers.PrimaryKeyRelatedField(read_only=True)
    client_name = serializers.SerializerMethodField(read_only=True)
    stylist_name = serializers.SerializerMethodField(read_only=True)
    service_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'branch', 'client', 'stylist', 'role', 'service', 'stylist_info',
            'status', 'created_at', 'description', 'updated_at', 'date_time', 'sale',
            'client_name', 'stylist_name', 'service_name'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        request = self.context.get('request')
        if not request:
            return attrs
        
        tenant = getattr(request, 'tenant', None)
        
        # SuperAdmin puede relacionar cualquier objeto
        if request.user.is_superuser:
            return attrs
        
        # Usuario sin tenant no puede crear appointments
        if not tenant:
            raise serializers.ValidationError(_('User without assigned tenant'))
        
        # Validar client pertenece al tenant
        client = attrs.get('client')
        if client and hasattr(client, 'tenant_id'):
            if client.tenant_id != tenant.id:
                raise serializers.ValidationError({
                    'client': _('Client does not belong to your tenant')
                })
        
        # Validar stylist pertenece al tenant
        stylist = attrs.get('stylist')
        if stylist and hasattr(stylist, 'tenant_id'):
            if stylist.tenant_id != tenant.id:
                raise serializers.ValidationError({
                    'stylist': _('Stylist does not belong to your tenant')
                })
        
        # Validar service pertenece al tenant
        service = attrs.get('service')
        if service and hasattr(service, 'tenant_id'):
            if service.tenant_id != tenant.id:
                raise serializers.ValidationError({
                    'service': _('Service does not belong to your tenant')
                })
        
        # Validar branch pertenece al tenant
        branch = attrs.get('branch')
        if branch and hasattr(branch, 'tenant_id'):
            if branch.tenant_id != tenant.id:
                raise serializers.ValidationError({
                    'branch': _('Branch does not belong to your tenant')
                })
        
        return attrs

    def validate_date_time(self, value):
        if value < timezone.now():
            raise serializers.ValidationError(_('Appointment date and time cannot be in the past'))
        return value

    def get_client_name(self, obj):
        if obj.client_id and obj.client:
            return obj.client.full_name
        return None

    def get_stylist_name(self, obj):
        if obj.stylist_id and obj.stylist:
            return obj.stylist.full_name or obj.stylist.email
        return None

    def get_service_name(self, obj):
        if obj.service_id and obj.service:
            return obj.service.name
        return None
