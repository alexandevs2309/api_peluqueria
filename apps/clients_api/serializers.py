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
        return attrs
