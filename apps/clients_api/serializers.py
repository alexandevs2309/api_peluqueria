from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from .models import Client

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'last_visit', 'loyalty_points', 'user', 'tenant']

    def validate(self, attrs):
        email = attrs.get('email')
        phone = attrs.get('phone')
        if not email and not phone:
            raise serializers.ValidationError("Debe proporcionar al menos un medio de contacto: correo electrónico o teléfono.")
        
        # Validación cross-tenant para preferred_stylist
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
        
        return attrs
