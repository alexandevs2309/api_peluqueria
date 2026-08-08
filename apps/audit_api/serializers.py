from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import AuditLog

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Serializador básico para usuarios"""
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name']

class AuditLogSerializer(serializers.ModelSerializer):
    """Serializador para el modelo AuditLog unificado"""
    
    user = UserSerializer(read_only=True)
    content_type_name = serializers.SerializerMethodField()
    object_repr = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'user',
            'action',
            'description',
            'content_type',
            'content_type_name',
            'object_id',
            'object_repr',
            'ip_address',
            'user_agent',
            'extra_data',
            'timestamp',
            'source'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_content_type_name(self, obj):
        """Retorna el nombre del tipo de contenido"""
        if obj.content_type:
            return obj.content_type.model
        return None
    
    def get_object_repr(self, obj):
        """Retorna una representación string del objeto relacionado"""
        try:
            if obj.content_type and obj.content_type.model_class() and obj.content_object:
                return str(obj.content_object)
        except (AttributeError, ValueError):
            pass
        return None

class AuditLogCreateSerializer(serializers.ModelSerializer):
    """Serializador para crear nuevos registros de auditoría"""
    
    class Meta:
        model = AuditLog
        fields = [
            'user',
            'action',
            'description',
            'content_type',
            'object_id',
            'ip_address',
            'user_agent',
            'extra_data',
            'source'
        ]
