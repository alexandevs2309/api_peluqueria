from rest_framework import serializers
from django.contrib.auth.models import Permission
from .models import Role


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ("id", "codename", "name", "content_type")


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), required=False
    )
    # Lista de IDs de usuarios que tienen este rol (solo lectura)
    assigned_users = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Role
        fields = ("id", "name", "description", "permissions", "assigned_users")
        extra_kwargs = {
            "permissions": {"required": False},
            "description": {"required": False, "allow_null": True, "allow_blank": True},
        }

    def get_assigned_users(self, obj):
        # Asegúrate de que el related_name exista en el modelo (user_roles_assignments)
        return list(obj.user_roles_assignments.values_list("user__id", flat=True))

    def validate_permissions(self, value):
        ids = [p.id for p in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("No se permiten permisos duplicados.")
        return value

    def create(self, validated_data):
        perms = validated_data.pop("permissions", [])
        role = Role.objects.create(**validated_data)
        if perms:
            role.permissions.set(perms)
        return role

    def update(self, instance, validated_data):
        perms = validated_data.pop("permissions", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if perms is not None:
            instance.permissions.set(perms)
        return instance
