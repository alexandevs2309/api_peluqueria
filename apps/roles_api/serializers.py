from rest_framework import serializers
from django.contrib.auth.models import Permission
from .models import Role
from django.contrib.auth import get_user_model

User = get_user_model()

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'codename', 'name', 'content_type']

class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all()
    )
    users = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), required=False
    )

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permissions', 'users']  # Asegúrate de que 'users' esté aquí
        extra_kwargs = {
            'users': {'required': False},
            'permissions': {'required': False},
        }

    def validate_permissions(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("No se permiten permisos duplicados.")
        return value

    def validate_users(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("No se permiten usuarios duplicados.")
        return value