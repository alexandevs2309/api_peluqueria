from django.utils import timezone
from django.utils.translation import gettext_lazy as _
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
        extra_kwargs = {'stylist_info': {'read_only': True}}

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
        
        return attrs

    def validate_date_time(self, value):
        if value < timezone.now():
            raise serializers.ValidationError(_('Appointment date and time cannot be in the past'))
        return value