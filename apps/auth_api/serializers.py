from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from .models import ActiveSession
from apps.tenants_api.models import Tenant

User = get_user_model()

class ActiveSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActiveSession
        fields = ['id', 'ip_address', 'user_agent', 'created_at', 'last_seen', 'is_active']

@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Registro de usuario',
            summary='Nuevo usuario con tenant',
            description='Registro de usuario asociado a un tenant existente',
            value={
                'email': 'nuevo@peluqueria.com',
                'full_name': 'Usuario Nuevo',
                'phone': '+1-809-555-0123',
                'password': 'password123',
                'tenant_subdomain': 'mi-peluqueria'
            },
            request_only=True,
        ),
    ]
)
class RegisterSerializer(serializers.ModelSerializer):
    """Registro de nuevo usuario en el sistema"""
    password = serializers.CharField(
        write_only=True, 
        min_length=8,
        help_text="Contraseña mínimo 8 caracteres",
        style={'input_type': 'password'}
    )
    tenant_subdomain = serializers.CharField(
        required=False,
        help_text="Subdominio del tenant (requerido para usuarios no-admin)"
    )
    phone = serializers.CharField(
        required=False,
        help_text="Teléfono de contacto (formato: +1-809-555-0123)"
    )

    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone', 'password', 'tenant_subdomain']
        extra_kwargs = {
            'email': {'help_text': 'Email único del usuario'},
            'full_name': {'help_text': 'Nombre completo del usuario'},
        }

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

@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Login con tenant',
            summary='Autenticación exitosa',
            description='Login de usuario con tenant específico',
            value={
                'email': 'admin@peluqueria.com',
                'password': 'password123',
                'tenant_subdomain': 'mi-peluqueria'
            },
            request_only=True,
        ),
    ]
)
class LoginSerializer(serializers.Serializer):
    """Autenticación de usuario con soporte multi-tenant"""
    email = serializers.EmailField(
        help_text="Email del usuario registrado"
    )
    password = serializers.CharField(
        help_text="Contraseña del usuario",
        style={'input_type': 'password'}
    )
    tenant_subdomain = serializers.CharField(
        required=False,
        help_text="Subdominio del tenant (opcional para SuperAdmin)"
    )

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
            # SuperAdmin puede no tener tenant
            if not tenant and user.role != 'SuperAdmin' and not user.is_superuser:
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
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    tenant = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone', 'password', 'tenant', 'role', 'is_active']

    def create(self, validated_data):
        # Asegurar que is_active sea True por defecto
        validated_data.setdefault('is_active', True)
        
        # Asignar tenant automáticamente si no se especifica
        request = self.context.get('request')
        print(f'🔍 [SERIALIZER] Request user: {request.user if request else "No request"}')
        print(f'🔍 [SERIALIZER] Request user tenant: {request.user.tenant if request and hasattr(request, "user") else "No tenant"}')
        print(f'🔍 [SERIALIZER] Validated data before: {validated_data}')
        
        if 'tenant' not in validated_data or validated_data['tenant'] is None:
            if request and hasattr(request, 'user') and request.user.tenant:
                validated_data['tenant'] = request.user.tenant
                print(f'🔍 [SERIALIZER] Tenant asignado: {request.user.tenant.id}')
        
        print(f'🔍 [SERIALIZER] Validated data after: {validated_data}')
        user = User.objects.create_user(**validated_data)
        print(f'🔍 [SERIALIZER] Usuario creado: ID={user.id}, Email={user.email}, Tenant={user.tenant_id}')
        return user
    
    def update(self, instance, validated_data):
        # No actualizar password en update
        validated_data.pop('password', None)
        
        # Manejar tenant correctamente
        tenant = validated_data.pop('tenant', None)
        if tenant is not None:
            instance.tenant = tenant
        
        # Actualizar otros campos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

class UserListSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    tenant = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'phone', 'role', 'tenant', 'tenant_name', 'is_active', 'date_joined', 'last_login']

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        if user.tenant:
            token['tenant_id'] = user.tenant.id
            token['tenant_subdomain'] = user.tenant.subdomain
        return token
