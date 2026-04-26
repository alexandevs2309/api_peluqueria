from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.core.exceptions import MultipleObjectsReturned
from .models import ActiveSession
from .role_utils import normalize_role_for_api, get_effective_role_api
from .settings_policy import (
    get_password_min_length,
    is_email_verification_required,
    is_mfa_globally_enabled,
)
from apps.tenants_api.models import Tenant
from apps.settings_api.utils import validate_employee_limit, maybe_auto_upgrade_employee_limit

User = get_user_model()
logger = logging.getLogger(__name__)


def get_explicit_tenant_input(data) -> str | None:
    tenant_input = data.get('tenant') or data.get('tenant_subdomain')
    return (tenant_input or '').strip().lower() or None


def extract_tenant_from_host(host: str) -> str | None:
    # FUTURE: Multi-tenant por subdominio
    # Cuando el sistema use dominios como:
    # cliente1.auron.com
    # cliente2.auron.com
    #
    # Se puede reintroducir la inferencia por host:
    # tenant_subdomain = extract_subdomain(request.get_host())
    #
    # PERO solo cuando:
    # - exista dominio propio
    # - DNS configurado
    # - wildcard SSL activo
    #
    # No usar HTTP_HOST directamente en entornos como Render/Netlify.
    return None


def validate_password_policy(password: str) -> str:
    min_length = get_password_min_length()
    if len(password or '') < min_length:
        raise serializers.ValidationError(
            f"La contraseña debe tener al menos {min_length} caracteres."
        )
    return password

class ActiveSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActiveSession
        fields = ['id', 'ip_address', 'user_agent', 'created_at', 'last_seen', 'is_active']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    tenant_subdomain = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone', 'password', 'tenant_subdomain']

    def validate_password(self, value):
        return validate_password_policy(value)

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
    tenant = serializers.CharField(required=False, allow_blank=True)
    tenant_subdomain = serializers.CharField(required=False, allow_blank=True)  # Alias legacy

    def validate(self, data):
        email = (data.get('email') or '').strip().lower()
        password = data.get('password')
        tenant_input = get_explicit_tenant_input(data)

        if not email:
            raise serializers.ValidationError({'email': 'El correo es requerido.'})

        # Persist normalized values for downstream consumers
        data['email'] = email
        if tenant_input:
            data['tenant'] = tenant_input
            data['tenant_subdomain'] = tenant_input

        # Login sin tenant es intencional y exclusivo para usuarios globales.
        if not tenant_input:
            try:
                superadmin = User.objects.get(email=email, is_superuser=True, tenant__isnull=True)
            except (User.DoesNotExist, MultipleObjectsReturned):
                pass
            else:
                if not superadmin.check_password(password):
                    raise serializers.ValidationError("Credenciales inválidas.")
                if not superadmin.is_active:
                    raise serializers.ValidationError("Cuenta inactiva. Contacte al administrador.")
                data['user'] = superadmin
                data['tenant'] = None
                return data

            raise serializers.ValidationError({
                'tenant': 'Tenant requerido para usuarios de cliente.'
            })

        # ✅ BUSCAR TENANT EXPLÍCITO
        try:
            tenant = Tenant.objects.get(subdomain=tenant_input, is_active=True, deleted_at__isnull=True)
        except Tenant.DoesNotExist:
            raise serializers.ValidationError("Credenciales inválidas.")

        # ✅ BUSCAR USUARIO SOLO EN ESE TENANT
        try:
            user = User.objects.get(email=email, tenant=tenant)
        except User.DoesNotExist:
            raise serializers.ValidationError("Credenciales inválidas.")

        # ✅ VALIDAR PASSWORD
        if not user.check_password(password):
            raise serializers.ValidationError("Credenciales inválidas.")

        # ✅ VALIDAR USUARIO ACTIVO
        if not user.is_active:
            raise serializers.ValidationError("Cuenta inactiva. Contacte al administrador.")

        if is_email_verification_required() and not getattr(user, 'is_email_verified', False):
            raise serializers.ValidationError("Debe verificar su correo antes de iniciar sesión.")

        data['user'] = user
        data['tenant'] = tenant
        return data

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()

    def validate_new_password(self, value):
        return validate_password_policy(value)

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    tenant = serializers.CharField(required=False, allow_blank=True)
    tenant_subdomain = serializers.CharField(required=False, allow_blank=True)

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField()

    def validate_new_password(self, value):
        return validate_password_policy(value)

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

    def validate_code(self, value):
        normalized = ''.join(str(value or '').split())
        if not normalized.isdigit() or len(normalized) != 6:
            raise serializers.ValidationError("Código inválido.")
        return normalized

class EmployeeUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    tenant = serializers.PrimaryKeyRelatedField(queryset=Tenant.objects.all(), required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone', 'password', 'tenant', 'role', 'is_active']

    def validate_password(self, value):
        return validate_password_policy(value)

    def create(self, validated_data):
        # Asegurar que is_active sea True por defecto
        validated_data.setdefault('is_active', True)
        # Usuarios creados por un administrador del tenant ya fueron autorizados
        # internamente; deben poder iniciar sesion sin verificacion publica.
        validated_data.setdefault('is_email_verified', True)
        
        # Asignar tenant automáticamente si no se especifica
        request = self.context.get('request')
        logger.debug('EmployeeUserSerializer.create request_user_id=%s', getattr(getattr(request, 'user', None), 'id', None))
        
        if 'tenant' not in validated_data or validated_data['tenant'] is None:
            if request and hasattr(request, 'user') and request.user.tenant:
                validated_data['tenant'] = request.user.tenant
                logger.debug('Tenant auto-assigned tenant_id=%s', request.user.tenant.id)

        tenant = validated_data.get('tenant')
        requested_role = validated_data.get('role')
        employee_roles = {'Cajera', 'Estilista', 'Manager', 'Client-Staff', 'Utility'}

        # Si el usuario que se crea será también empleado, validar el límite aquí
        # porque el Employee se genera por signal después del alta del User.
        if tenant and requested_role in employee_roles:
            plan_type = getattr(tenant, 'plan_type', 'basic')
            if not validate_employee_limit(tenant, plan_type):
                upgrade_result = maybe_auto_upgrade_employee_limit(tenant, changed_by=getattr(request, 'user', None))
                tenant.refresh_from_db(fields=['plan_type', 'subscription_plan', 'max_employees', 'max_users', 'settings', 'updated_at'])
                plan_type = getattr(tenant, 'plan_type', plan_type)

                if not validate_employee_limit(tenant, plan_type):
                    error_message = f'Su plan {plan_type} no permite más empleados. Actualice su plan.'
                    if upgrade_result.get('reason') == 'no_higher_plan':
                        error_message = 'Ya se alcanzó el plan más alto disponible y no hay más capacidad automática para empleados.'
                    raise serializers.ValidationError({
                        'error': 'Límite de empleados alcanzado',
                        'message': error_message,
                        'limit': tenant.max_employees,
                        'current': tenant.employees.filter(is_active=True).count() if hasattr(tenant, 'employees') else None,
                    })
        
        user = User.objects.create_user(**validated_data)
        logger.info('Employee user created user_id=%s tenant_id=%s', user.id, user.tenant_id)
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
    avatar_url = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'phone', 'role', 'tenant', 'tenant_name', 'is_active', 'mfa_enabled', 'date_joined', 'last_login', 'avatar_url']

    def get_avatar_url(self, obj):
        return obj.avatar.url if obj.avatar else None

    def get_role(self, obj):
        return get_effective_role_api(obj, tenant=getattr(obj, 'tenant', None))

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        if user.tenant:
            token['tenant_id'] = user.tenant.id
            token['tenant_subdomain'] = user.tenant.subdomain
        return token
