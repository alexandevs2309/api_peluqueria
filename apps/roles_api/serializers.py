from rest_framework import serializers
from django.contrib.auth.models import Permission
from apps.auth_api.models import User
from .models import Role


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'codename', 'name', 'content_type']

class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), required=False
    )
    assigned_users = serializers.SerializerMethodField()  # ✅ Esto es obligatorio

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permissions', 'assigned_users']
        extra_kwargs = {
            'permissions': {'required': False},
        }

    def get_assigned_users(self, obj):
        # Asegúrate de que el modelo Role tenga la relación user_roles_assignments
        return list(obj.user_roles_assignments.values_list('user__id', flat=True))

    def validate_permissions(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("No se permiten permisos duplicados.")
        return value
