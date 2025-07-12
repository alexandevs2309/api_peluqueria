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
        many=True, queryset=Permission.objects.all() ,required=False
    )
    # users = serializers.PrimaryKeyRelatedField(pero ya hice eso
    #     many=True, queryset=User.objects.all(), required=False
    # )

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permissions' ,'assigned_users']
        extra_kwargs = {
            # 'users': {'required': False},
            'permissions': {'required': False},
        }

    def get_assigned_users(self, obj):
        return list(obj.user_roles_assignments.values_list('user__id', flat=True))

    def validate_permissions(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("No se permiten permisos duplicados.")
        return value

   