import sys
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from .tasks import send_email_async
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema
from .serializers import (
    ActiveSessionSerializer, RegisterSerializer, LoginSerializer,
    PasswordChangeSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, MFASetupSerializer, MFAVerifySerializer,
    EmployeeUserSerializer, UserListSerializer
)
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework import viewsets
from rest_framework.decorators import action
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan
from apps.roles_api.models import Role, UserRole
import re
from .models import LoginAudit, AccessLog, ActiveSession
from .utils import get_client_ip, get_user_agent, get_client_jti
from .anti_fraud import AntiFraudValidator
from django.utils.timezone import now
import pyotp
import qrcode
from io import BytesIO
from base64 import b64encode


User = get_user_model()

class RegisterThrottle(AnonRateThrottle):
    scope = 'register'

class LoginThrottle(AnonRateThrottle):
    scope = 'login'

class PasswordResetThrottle(AnonRateThrottle):
    scope = 'password_reset'

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle]

    def perform_create(self, serializer):
        # Obtener datos para validación
        email = serializer.validated_data['email']
        ip_address = get_client_ip(self.request)
        
        # Validación anti-fraude ANTES de crear tenant
        is_fraud, reason, blocked_until = AntiFraudValidator.check_email_fraud(email, ip_address)
        if is_fraud:
            error_messages = {
                'EMAIL_ALREADY_USED_FREE': 'Este email ya fue usado para una cuenta gratuita',
                'IP_LIMIT_EXCEEDED': 'Límite de cuentas gratuitas alcanzado desde esta IP',
                'EMAIL_LIMIT_EXCEEDED': 'Este email ya tiene una cuenta gratuita'
            }
            raise ValidationError({
                'email': error_messages.get(reason, 'No se puede crear la cuenta'),
                'code': reason,
                'blocked_until': blocked_until.isoformat() if blocked_until else None
            })
        
        user = serializer.save()
        
        # Crear tenant automáticamente para el usuario
        try:
            # Obtener plan FREE por defecto para nuevos registros
            free_plan = SubscriptionPlan.objects.filter(name='free').first()
            if not free_plan:
                free_plan = SubscriptionPlan.objects.filter(name='basic').first()
            if not free_plan:
                free_plan = SubscriptionPlan.objects.first()
            
            # Crear subdomain único
            subdomain = re.sub(r'[^a-zA-Z0-9]', '', user.full_name.lower())[:50]
            if not subdomain:
                subdomain = 'barbershop'
            
            counter = 1
            original_subdomain = subdomain
            while Tenant.objects.filter(subdomain=subdomain).exists():
                subdomain = f'{original_subdomain}{counter}'
                counter += 1
            
            # Crear nombre de tenant único
            tenant_name = f'Barbería de {user.full_name}'
            counter = 1
            original_name = tenant_name
            while Tenant.objects.filter(name=tenant_name).exists():
                tenant_name = f'{original_name} {counter}'
                counter += 1
            
            # Crear tenant
            tenant = Tenant.objects.create(
                name=tenant_name,
                subdomain=subdomain,
                owner=user,
                subscription_plan=free_plan,
                is_active=True
            )
            
            # Asignar tenant al usuario
            user.tenant = tenant
            user.save()
            
            # Asignar rol Client-Admin
            client_admin_role = Role.objects.get(name='Client-Admin')
            UserRole.objects.create(
                user=user,
                role=client_admin_role,
                tenant=tenant
            )
            
            # Registrar en sistema anti-fraude si es plan FREE
            if free_plan and free_plan.name == 'free':
                AntiFraudValidator.record_free_signup(user.email, get_client_ip(self.request))
            
            print(f'Usuario {user.email} creado con tenant {tenant.name} y rol Client-Admin')
                
        except Exception as e:
            print(f'Error creando tenant y rol: {e}')
            import traceback
            traceback.print_exc()
        
        email_subject = "Verifica tu correo"
        email_body = f"Hola {user.full_name}, verifica tu correo en: http://localhost:4200/verify-email/{user.email_verification_token}/"
        email_from = "no-reply@peluqueria.com"
        email_to = [user.email]
        
        if "pytest" in sys.modules:
            send_email_async(email_subject, email_body, email_from, email_to)
        else:
            send_email_async.delay(email_subject, email_body, email_from, email_to)
        
        # No devolver Response desde perform_create, solo procesar
        # La respuesta se maneja automáticamente por CreateAPIView

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    @method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        # Rate limit por tenant
        tenant_subdomain = request.META.get('HTTP_HOST', '').split('.')[0] if '.' in request.META.get('HTTP_HOST', '') else request.data.get('tenant_subdomain')
        if tenant_subdomain:
            from django_ratelimit.core import is_ratelimited
            if is_ratelimited(request, group='tenant_login', key=lambda r: tenant_subdomain, rate='20/m', method='POST'):
                return Response({"detail": "Demasiados intentos de login para este tenant."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            email = request.data.get('email')

            tenant_subdomain = request.META.get('HTTP_HOST', '').split('.')[0] if '.' in request.META.get('HTTP_HOST', '') else None
            if tenant_subdomain:
                try:
                    tenant = Tenant.objects.get(subdomain=tenant_subdomain)
                    user = User.objects.filter(email=email, tenant=tenant).first()
                except (Tenant.DoesNotExist, User.DoesNotExist):
                    user = None
            else:
                user = User.objects.filter(email=email).first()
            
            LoginAudit.objects.create(
                user=user,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                successful=False,
                message=f"Credenciales inválidas - Tenant: {tenant_subdomain or 'unknown'}",
                timestamp=now()
            )
            raise
        
        user = serializer.validated_data['user']
        tenant = serializer.validated_data['tenant']

        if not tenant and user.role != 'SuperAdmin':
            return Response({"detail": "Usuario sin tenant asignado. Contacte al administrador."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            LoginAudit.objects.create(
                user=user,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                successful=False,
                message="Cuenta inactiva",
                timestamp=now()
            )
            return Response({"detail": "Cuenta inactiva. Contacte al administrador."}, status=status.HTTP_403_FORBIDDEN)

        if user.mfa_enabled:
            return Response({
                "detail": "Se requiere verificación MFA.",
                "email": user.email,
                "tenant": {"id": tenant.id, "subdomain": tenant.subdomain}
            }, status=status.HTTP_200_OK)

        refresh = RefreshToken.for_user(user)
        if tenant:
            refresh['tenant_id'] = tenant.id
            refresh['tenant_subdomain'] = tenant.subdomain
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        jti = get_client_jti(access_token)

        ActiveSession.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            token_jti=jti,
            refresh_token=refresh_token,
            is_active=True,
            tenant=tenant
        )

        AccessLog.objects.create(
            user=user,
            event_type='LOGIN',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            timestamp=now()
        )
        LoginAudit.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            successful=True,
            message="Inicio de sesión exitoso",
            timestamp=now()
        )

        user_role = user.role or 'ClientStaff'
        if not user_role and user.roles.exists():
            user_role = user.roles.first().name
        
        response_data = {
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user_role,
            },
            'access': access_token,
            'refresh': refresh_token
        }
        
        if tenant:
            response_data['tenant'] = {
                'id': tenant.id,
                'name': tenant.name,
                'subdomain': tenant.subdomain,
            }

        # response.set_cookie(
        #     'access_token',
        #     value=access_token,
        #     httponly=True,
        #     secure=not settings.DEBUG,
        #     samesite='Strict',
        #     max_age=15 * 60,
        #     path='/'
        # )
        # response.set_cookie(
        #     'refresh_token',
        #     value=refresh_token,
        #     httponly=True,
        #     secure=not settings.DEBUG,
        #     samesite='Strict',
        #     max_age=24 * 60 * 60,
        #     path='/'
        # )
        response = Response(response_data)
        if tenant:
            response.set_cookie('tenant_id', str(tenant.id), httponly=False, secure=not settings.DEBUG, samesite='Strict')
        return response

class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Try to get refresh_token from cookies first, then from body
        refresh_token = request.COOKIES.get('refresh_token') or request.data.get('refresh_token')
        
        # Always return success response
        response = Response({"detail": "Sesión cerrada exitosamente."}, status=status.HTTP_200_OK)
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                
                # Try to find and expire session
                try:
                    session = ActiveSession.objects.get(refresh_token=refresh_token)
                    session.expire_session()
                    
                    # Log successful logout if we have a user
                    if hasattr(request, 'user') and request.user.is_authenticated:
                        AccessLog.objects.create(
                            user=request.user,
                            event_type='LOGOUT',
                            ip_address=get_client_ip(request),
                            user_agent=get_user_agent(request),
                            timestamp=now()
                        )
                except ActiveSession.DoesNotExist:
                    pass
                    
            except TokenError:
                # Token invalid/expired, but still return success
                pass
        
        return response

class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = PasswordChangeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            if not user.check_password(serializer.validated_data.get("old_password")):
                return Response({"old_password": ["Contraseña incorrecta."]}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(serializer.validated_data.get("new_password"))
            user.save()

            AccessLog.objects.create(
                user=user,
                event_type='PASSWORD_CHANGE',
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                timestamp=now()
            )

            if "pytest" in sys.modules:
                send_mail(
                    "Cambio de contraseña exitoso",
                    f"Hola {user.full_name}, tu contraseña ha sido cambiada exitosamente.",
                    "no-reply@peluqueria.com",
                    [user.email]
                )
            else:
                send_email_async.delay(
                    "Cambio de contraseña exitoso",
                    f"Hola {user.full_name}, tu contraseña ha sido cambiada exitosamente.",
                    "no-reply@peluqueria.com",
                    [user.email]
                )

            return Response({"detail": "Contraseña actualizada correctamente."})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(email=serializer.validated_data['email'])
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"http://localhost:4200/reset-password/{uid}/{token}/"

            AccessLog.objects.create(
                user=user,
                event_type='PASSWORD_RESET_REQUEST',
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                timestamp=now()
            )

            if "pytest" in sys.modules:
                send_mail(
                    "Restablecer contraseña",
                    f"Hola {user.full_name}, para restablecer tu contraseña haz clic en el siguiente enlace:\n{reset_url}",
                    "no-reply@peluqueria.com",
                    [user.email]
                )
            else:
                send_email_async.delay(
                    "Restablecer contraseña",
                    f"Hola {user.full_name}, para restablecer tu contraseña haz clic en el siguiente enlace:\n{reset_url}",
                    "no-reply@peluqueria.com",
                    [user.email]
                )

            return Response({"detail": "Correo enviado para restablecer contraseña."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"detail": "Correo enviado si el usuario existe."}, status=status.HTTP_200_OK)

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        AccessLog.objects.create(
            user=user,
            event_type='PASSWORD_RESET_CONFIRM',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            timestamp=now()
        )

        if "pytest" in sys.modules:
            send_mail(
                "Contraseña restablecida",
                f"Hola {user.full_name}, tu contraseña ha sido restablecida exitosamente.",
                "no-reply@peluqueria.com",
                [user.email]
            )
        else:
            send_email_async.delay(
                "Contraseña restablecida",
                f"Hola {user.full_name}, tu contraseña ha sido restablecida exitosamente.",
                "no-reply@peluqueria.com",
                [user.email]
            )

        return Response({"detail": "Contraseña restablecida con éxito."})

@extend_schema(
    responses={200: ActiveSessionSerializer(many=True)},
    description="Lista de sesiones activas del usuario autenticado."
)
class ActiveSessionsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ActiveSessionSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ActiveSession.objects.none()
        return ActiveSession.objects.filter(user=self.request.user, is_active=True)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)  # Aplicar paginación
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            AccessLog.objects.create(
                user=request.user,
                event_type='ACTIVE_SESSIONS_VIEW',
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                timestamp=now()
            )
            return self.get_paginated_response(serializer.data)  # Devolver respuesta paginada
        serializer = self.get_serializer(queryset, many=True)
        AccessLog.objects.create(
            user=request.user,
            event_type='ACTIVE_SESSIONS_VIEW',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            timestamp=now()
        )
        return Response(serializer.data)

class TerminateSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, jti):
        try:
            session = ActiveSession.objects.get(token_jti=jti, user=request.user, is_active=True)
            session.expire_session()
            AccessLog.objects.create(
                user=request.user,
                event_type='SESSION_TERMINATED',
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                timestamp=now()
            )
            return Response({"detail": "Sesión terminada exitosamente."}, status=status.HTTP_200_OK)
        except ActiveSession.DoesNotExist:
            raise NotFound("Sesión no encontrada o ya terminada.")

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            user = User.objects.get(email_verification_token=token)
            user.is_email_verified = True
            user.email_verification_token = None
            user.save()
            AccessLog.objects.create(
                user=user,
                event_type='EMAIL_VERIFIED',
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                timestamp=now()
            )
            return Response({"detail": "Correo verificado exitosamente."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)

class MFASetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.mfa_enabled:
            return Response({"error": "MFA ya está habilitado."}, status=status.HTTP_400_BAD_REQUEST)

        secret = pyotp.random_base32()
        user.mfa_secret = secret
        user.save()

        totp = pyotp.TOTP(secret)
        qr_uri = totp.provisioning_uri(user.email, issuer_name="HairSalon")
        qr = qrcode.make(qr_uri)
        buffer = BytesIO()
        qr.save(buffer)
        qr_code = b64encode(buffer.getvalue()).decode()

        AccessLog.objects.create(
            user=user,
            event_type='MFA_SETUP',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            timestamp=now()
        )
        return Response({"qr_code": qr_code, "secret": secret})

class MFAVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        totp = pyotp.TOTP(user.mfa_secret)
        if totp.verify(serializer.validated_data['code']):
            user.mfa_enabled = True
            user.save()
            AccessLog.objects.create(
                user=user,
                event_type='MFA_VERIFIED',
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                timestamp=now()
            )
            return Response({"detail": "MFA verificado y habilitado."})
        return Response({"error": "Código inválido."}, status=status.HTTP_400_BAD_REQUEST)

class MFALoginVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = request.data.get('email')
        tenant_subdomain = request.META.get('HTTP_HOST', '').split('.')[0] if '.' in request.META.get('HTTP_HOST', '') else request.data.get('tenant_subdomain')
        

        if not tenant_subdomain:
            return Response({"error": "Tenant requerido."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            tenant = Tenant.objects.get(subdomain=tenant_subdomain)
            user = User.objects.get(email=email, tenant=tenant)
        except (Tenant.DoesNotExist, User.DoesNotExist):
            return Response({"error": "Usuario o tenant no encontrado."}, status=status.HTTP_400_BAD_REQUEST)

        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(serializer.validated_data['code']):
            LoginAudit.objects.create(
                user=user,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                successful=False,
                message="Código MFA inválido",
                timestamp=now()
            )
            return Response({"error": "Código MFA inválido."}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        jti = get_client_jti(access_token)

        ActiveSession.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            token_jti=jti,
            refresh_token=refresh_token,
            is_active=True,
            tenant=tenant
        )

        AccessLog.objects.create(
            user=user,
            event_type='LOGIN_MFA',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            timestamp=now()
        )
        LoginAudit.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            successful=True,
            message="Inicio de sesión con MFA exitoso",
            timestamp=now()
        )

        response = Response({
            'user': {
                'email': user.email,
                'full_name': user.full_name,
                'is_superuser': user.is_superuser
            },
            'access': access_token,
            'refresh': refresh_token
        })

        response.set_cookie(
            'access_token',
            value=access_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Strict',
            max_age=15 * 60,
            path='/'
        )
        response.set_cookie(
            'refresh_token',
            value=refresh_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Strict',
            max_age=24 * 60 * 60,
            path='/'
        )

        return response



class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = UserListSerializer
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy to add logging and proper deletion"""
        instance = self.get_object()
        print(f"Attempting to delete user: {instance.email} (ID: {instance.id})")
        
        # Check if user can be deleted
        if instance.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
            return Response({
                'error': 'Cannot delete the last superuser'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Log the deletion
            AccessLog.objects.create(
                user=request.user,
                event_type='USER_DELETED',
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                timestamp=now()
            )
            
            # Perform the deletion
            self.perform_destroy(instance)
            print(f"User {instance.email} deleted successfully")
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            print(f"Error deleting user: {str(e)}")
            return Response({
                'error': f'Failed to delete user: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    def perform_destroy(self, instance):
        """Actually delete the user instance"""
        instance.delete()
    
    def get_serializer_class(self):
        if self.action in ['create']:
            return EmployeeUserSerializer
        return UserListSerializer

    def create(self, request, *args, **kwargs):
        # Check user limits for non-superadmin
        if not request.user.is_superuser and request.user.tenant:
            if not request.user.tenant.can_add_user():
                return Response({
                    'error': 'User limit reached for your plan',
                    'current': request.user.tenant.get_user_usage()['current'],
                    'limit': request.user.tenant.max_users
                }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = serializer.save()
            return Response({
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return User.objects.all()
        elif user.tenant:
            return User.objects.filter(tenant=user.tenant)
        return User.objects.none()

    @action(detail=False, methods=['get'])
    def available_for_employee(self, request):
        """Usuarios disponibles para ser empleados"""
        users = self.get_queryset().filter(tenant__isnull=False)
        return Response([{
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'tenant_id': user.tenant_id,
            'roles': [{'id': role.id, 'name': role.name} for role in user.roles.all()]
        } for user in users])