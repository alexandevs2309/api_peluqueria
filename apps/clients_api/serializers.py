from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from .models import Client

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            'id', 'full_name', 'email', 'phone', 'birthday', 'gender',
            'preferred_stylist', 'loyalty_points', 'last_visit', 'source',
            'notes', 'is_active', 'created_by', 'created_at', 'updated_at',
            'user', 'tenant', 'branch',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'last_visit', 'loyalty_points', 'user', 'tenant']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and not getattr(request.user, 'is_superuser', False):
            tenant = getattr(request, 'tenant', None)
            if tenant:
                from django.contrib.auth import get_user_model
                from apps.settings_api.models import Branch
                User = get_user_model()
                self.fields['preferred_stylist'].queryset = User.objects.filter(tenant=tenant)
                self.fields['branch'].queryset = Branch.objects.filter(tenant=tenant)

    def validate(self, attrs):
        email = attrs.get('email')
        phone = attrs.get('phone')
        if not email and not phone:
            raise serializers.ValidationError("Debe proporcionar al menos un medio de contacto: correo electrónico o teléfono.")
        
        # Validación cross-tenant para preferred_stylist y branch
        request = self.context.get('request')
        if request and not request.user.is_superuser:
            tenant = getattr(request, 'tenant', None)
            
            if not tenant:
                raise serializers.ValidationError(_('User without assigned tenant'))
            
            preferred_stylist = attrs.get('preferred_stylist')
            if preferred_stylist and hasattr(preferred_stylist, 'tenant_id'):
                if preferred_stylist.tenant_id != tenant.id:
                    raise serializers.ValidationError({
                        'preferred_stylist': _('Stylist does not belong to your tenant')
                    })
            
            branch = attrs.get('branch')
            if branch and hasattr(branch, 'tenant_id'):
                if branch.tenant_id != tenant.id:
                    raise serializers.ValidationError({
                        'branch': _('Branch does not belong to your tenant')
                    })
        
        return attrs
