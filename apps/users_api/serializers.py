<<<<<<< HEAD
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.roles_api.models import Role, UserRole
from apps.roles_api.serializers import RoleSerializer
from apps.auth_api.models import AccessLog
=======
from django.contrib.auth import get_user_model
from rest_framework import serializers
>>>>>>> origin/master

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
<<<<<<< HEAD
    roles = RoleSerializer(many=True, read_only=True)
    role_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Role.objects.all(),
        source='roles'
    )
    assigned_users = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'full_name',
            'email',
            'password',
            'assigned_users',
            'is_active',
            'date_joined',
            'roles',
            'role_ids'
        ]
        read_only_fields = ['id', 'date_joined']

    def get_assigned_users(self, obj):
        return [ur.role.name for ur in obj.user_roles.all()]

    def create(self, validated_data):
        roles = validated_data.pop('roles', [])
        password = validated_data.pop('password', None)
        
        if User.objects.filter(email=validated_data['email']).exists():
            raise serializers.ValidationError({"email": "Este correo ya está registrado."})


=======

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'roles', 'is_active', 'password', 'date_joined']
        read_only_fields = ['id', 'date_joined']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
>>>>>>> origin/master
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
<<<<<<< HEAD

        for role in roles:

            if len(set([r.id for r in roles])) != len(roles):
                    raise serializers.ValidationError({"roles": "No se pueden asignar roles duplicados."})
            UserRole.objects.create(user=user, role=role)

        return user


    def update(self, instance, validated_data):
        roles = validated_data.pop('roles', None)
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)
        instance.save()

        if roles is not None:
            instance.user_roles.all().delete()
            for role in roles:

                if len(set([r.id for r in roles])) != len(roles):
                    raise serializers.ValidationError({"roles": "No se pueden asignar roles duplicados."})
                UserRole.objects.create(user=instance, role=role)

        return instance
    
class AccessLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessLog
        fields = ['event_type', 'timestamp', 'ip_address', 'user_agent']

=======
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
>>>>>>> origin/master
