from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, ActiveSession
from apps.roles_api.models import Role , UserRole
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.translation import gettext_lazy as _
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from apps.roles_api.models import Role, UserRole

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)


    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone', 'password', 'password2']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Las contraseñas no coinciden.")
        return data

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este correo ya está registrado.")
        return value

    def validate_phone(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("El teléfono debe contener solo números.")
        if len(value) < 10:
            raise serializers.ValidationError("El número de teléfono es muy corto.")
        return value

    def validate_full_name(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("El nombre completo es muy corto.")
        return value

    

    def create(self, validated_data):
        validated_data.pop('password2')
        

        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data.get('full_name'),
            phone=validated_data.get('phone')
           
        )
        try:
            client_role = Role.objects.get(name='Client') # Asegúrate de que este rol exista en tu DB
            UserRole.objects.create(user=user, role=client_role)
        except Role.DoesNotExist:
            print("Advertencia: El rol 'Client' no existe. Asegúrate de crearlo en la base de datos.")
            

        user.email_verification_token = default_token_generator.make_token(user)
        user.save()
        return user
    

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError(_('Credenciales inválidas.'))
        if not user.is_active:
            raise serializers.ValidationError(_('Esta cuenta está desactivada.'))
       
        refresh = RefreshToken.for_user(user)
        self.user = user
        return {
            'user': user,
            'email': user.email,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8, validators=[validate_password])
    new_password2 = serializers.CharField(required=True, write_only=True, min_length=8)

    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError("Las contraseñas no coinciden.")
        return data

 

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password], write_only=True)

    def validate(self, attrs):
        try:
            uid = force_str(urlsafe_base64_decode(attrs['uid']))
            self.user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            raise serializers.ValidationError("Token inválido.")

        if not default_token_generator.check_token(self.user, attrs['token']):
            raise serializers.ValidationError("Token inválido o expirado.")

        return attrs

    def save(self):
        self.user.set_password(self.validated_data['new_password'])
        self.user.save()
        return self.user

class ActiveSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActiveSession
        fields = ['id', 'ip_address', 'user_agent', 'token_jti', 'created_at', 'last_seen', 'is_active']

class MFASetupSerializer(serializers.Serializer):
    qr_code = serializers.CharField(read_only=True)
    secret = serializers.CharField(read_only=True)

class MFAVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)