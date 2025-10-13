from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from .models import ActiveSession
from apps.tenants_api.models import Tenant

User = get_user_model()

class ActiveSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActiveSession
        fields = ['id', 'ip_address', 'user_agent', 'created_at', 'last_seen', 'is_active']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    tenant_subdomain = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone', 'password', 'tenant_subdomain']

    def create(self, validated_data):
        tenant_subdomain = validated_data.pop('tenant_subdomain', None)
        tenant = None
        if tenant_subdomain:
            try:
                tenant = Tenant.objects.get(subdomain=tenant_subdomain)
            except Tenant.DoesNotExist:
                raise serializers.ValidationError("Tenant no encontrado.")
        user = User.objects.create_user(**validated_data)
        if tenant:
            user.tenant = tenant
            user.save()
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    tenant_subdomain = serializers.CharField(required=False)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        tenant_subdomain = data.get('tenant_subdomain')

        if tenant_subdomain:
            try:
                tenant = Tenant.objects.get(subdomain=tenant_subdomain)
                user = User.objects.get(email=email, tenant=tenant)
            except (Tenant.DoesNotExist, User.DoesNotExist):
                raise serializers.ValidationError("Credenciales inválidas.")
        else:
            user = User.objects.filter(email=email).first()
            if not user:
                raise serializers.ValidationError("Credenciales inválidas.")
            tenant = user.tenant
            if not tenant and user.role != 'SuperAdmin':
                raise serializers.ValidationError("Usuario sin tenant asignado.")

        if not user.check_password(password):
            raise serializers.ValidationError("Credenciales inválidas.")

        data['user'] = user
        data['tenant'] = tenant
        return data

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate(self, data):
        try:
            uid = force_str(urlsafe_base64_decode(data['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Token inválido.")

        if not default_token_generator.check_token(user, data['token']):
            raise serializers.ValidationError("Token inválido.")

        data['user'] = user
        return data

    def save(self):
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

class MFASetupSerializer(serializers.Serializer):
    pass

class MFAVerifySerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=6)

class EmployeeUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone', 'password', 'tenant']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class UserListSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'phone', 'role', 'tenant_name', 'is_active', 'date_joined', 'last_login']

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        if user.tenant:
            token['tenant_id'] = user.tenant.id
            token['tenant_subdomain'] = user.tenant.subdomain
        return token
