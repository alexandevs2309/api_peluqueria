import sys
import logging
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
    EmployeeUserSerializer, UserListSerializer, get_explicit_tenant_input
)
from .role_utils import normalize_role_for_api, get_effective_role_name, get_effective_role_api
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework import viewsets
from rest_framework.decorators import action
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan
from apps.roles_api.models import Role, UserRole
import re
from html import escape
from datetime import timedelta
from .models import LoginAudit, AccessLog, ActiveSession
from .utils import get_client_ip, get_user_agent, get_client_jti
from .settings_policy import is_mfa_globally_enabled, get_jwt_expiry_minutes
from .login_policy import is_login_locked_out, get_login_lockout_message
from .cookie_utils import set_auth_cookies
from apps.settings_api.utils import maybe_auto_upgrade_user_limit

from django.utils.timezone import now
import pyotp
import qrcode
from io import BytesIO
from base64 import b64encode
from .authentication import DualJWTAuthentication


from apps.roles_api.role_hierarchy import validate_role_assignment, get_allowed_roles, can_modify_user
from apps.core.tenant_permissions import TenantPermissionByAction


User = get_user_model()
logger = logging.getLogger(__name__)

# Helper function to safely create audit logs
def safe_create_login_audit(user, request, successful, message):
    """Crear LoginAudit truncando campos largos"""
    return LoginAudit.objects.create(
        user=user,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)[:255] if get_user_agent(request) else '',
        successful=successful,
        message=str(message)[:255] if message else '',
        timestamp=now()
    )

def safe_create_access_log(user, event_type, request):
    """Crear AccessLog truncando campos largos"""
    return AccessLog.objects.create(
        user=user,
        event_type=event_type,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)[:255] if get_user_agent(request) else '',
        timestamp=now()
    )


def issue_refresh_for_user(user, tenant=None):
    refresh = RefreshToken.for_user(user)
    access_token = refresh.access_token
    access_token.set_exp(lifetime=timedelta(minutes=get_jwt_expiry_minutes()))

    if tenant:
        refresh['tenant_id'] = tenant.id
        refresh['tenant_subdomain'] = tenant.subdomain

    return refresh, access_token

def _resolve_business_branding(user, request=None):
    business_name = 'Auron Suite'
    logo_url = ''

    if getattr(user, 'tenant', None):
        try:
            from apps.settings_api.barbershop_models import BarbershopSettings
            shop_settings = BarbershopSettings.objects.filter(tenant=user.tenant).first()
            if shop_settings:
                business_name = shop_settings.name or business_name
                if shop_settings.logo:
                    raw_logo = shop_settings.logo.url
                    if request is not None:
                        logo_url = request.build_absolute_uri(raw_logo)
                    else:
                        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:4200').rstrip('/')
                        logo_url = f"{frontend_url}{raw_logo}" if raw_logo.startswith('/') else f"{frontend_url}/{raw_logo}"
        except Exception:
            pass

        if user.tenant.name and business_name == 'Auron Suite':
            business_name = user.tenant.name

    return business_name, logo_url

def _build_branded_email_html(user, title, message_html, cta_url=None, cta_label=None, request=None):
    business_name, logo_url = _resolve_business_branding(user, request=request)
    safe_title = escape(title)
    safe_business_name = escape(business_name)
    logo_block = f'<img src="{escape(logo_url)}" alt="Logo" style="max-height:64px;max-width:180px;object-fit:contain;margin-bottom:12px;" />' if logo_url else ''
    cta_block = (
        f'<p style="margin:24px 0;"><a href="{escape(cta_url)}" '
        'style="background:#2563eb;color:#fff;text-decoration:none;padding:10px 16px;border-radius:8px;display:inline-block;font-weight:600;">'
        f'{escape(cta_label or "Abrir enlace")}</a></p>'
    ) if cta_url else ''

    return f"""
    <div style="font-family:Arial,sans-serif;background:#f8fafc;padding:20px;">
      <div style="max-width:620px;margin:0 auto;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:24px;">
        <div style="text-align:center;border-bottom:1px solid #e5e7eb;padding-bottom:12px;margin-bottom:16px;">
          {logo_block}
          <h2 style="margin:0;color:#111827;">{safe_business_name}</h2>
        </div>
        <h3 style="margin:0 0 12px 0;color:#111827;">{safe_title}</h3>
        <div style="color:#374151;font-size:14px;line-height:1.6;">{message_html}</div>
        {cta_block}
      </div>
    </div>
    """

def _deliver_user_email(user, subject, text_body, html_body):
    email_from = "no-reply@peluqueria.com"
    recipients = [user.email]
    if "pytest" in sys.modules:
        send_mail(subject, text_body, email_from, recipients, html_message=html_body)
    else:
        send_email_async.delay(subject, text_body, email_from, recipients, html_message=html_body)

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
        from django.db import transaction
        
        email = serializer.validated_data['email']
        
        # Transacción atómica para garantizar tenant antes de usuario
        with transaction.atomic():
            # Plan de onboarding para iniciar el tenant en trial sin exponer un plan gratis permanente en la oferta publica.
            starter_plan = SubscriptionPlan.objects.filter(name='free').first()
            if not starter_plan:
                starter_plan = SubscriptionPlan.objects.filter(name='basic').first()
            if not starter_plan:
                starter_plan = SubscriptionPlan.objects.first()
            
            # Crear subdomain único
            full_name = serializer.validated_data.get('full_name', 'barbershop')
            subdomain = re.sub(r'[^a-zA-Z0-9]', '', full_name.lower())[:50]
            if not subdomain:
                subdomain = 'barbershop'
            
            counter = 1
            original_subdomain = subdomain
            while Tenant.objects.filter(subdomain=subdomain).exists():
                subdomain = f'{original_subdomain}{counter}'
                counter += 1
            
            # Crear nombre de tenant único
            tenant_name = f'Barbería de {full_name}'
            counter = 1
            original_name = tenant_name
            while Tenant.objects.filter(name=tenant_name).exists():
                tenant_name = f'{original_name} {counter}'
                counter += 1
            
            # Crear tenant PRIMERO
            tenant = Tenant.objects.create(
                name=tenant_name,
                subdomain=subdomain,
                owner=None,
                subscription_plan=starter_plan,
                is_active=True
            )
            
            # Crear usuario con tenant asignado
            user = serializer.save(tenant=tenant)
            
            # Actualizar owner del tenant
            tenant.owner = user
            tenant.save(update_fields=['owner'])
            
            # Asignar rol Client-Admin
            try:
                client_admin_role = Role.objects.get(name='Client-Admin')
                UserRole.objects.create(
                    user=user,
                    role=client_admin_role,
                    tenant=tenant
                )
            except Role.DoesNotExist:
                pass
        
        # Enviar email de verificación (fuera de transacción)
        email_subject = "Verifica tu correo"
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:4200').rstrip('/')
        verify_url = f"{frontend_url}/verify-email/{user.email_verification_token}/"
        email_body = f"Hola {user.full_name}, verifica tu correo en: {verify_url}"
        email_html = _build_branded_email_html(
            user=user,
            title=email_subject,
            message_html=(
                f"<p>Hola {escape(user.full_name or user.email)},</p>"
                "<p>Activa tu cuenta para continuar usando la plataforma.</p>"
            ),
            cta_url=verify_url,
            cta_label="Verificar correo"
        )
        _deliver_user_email(user, email_subject, email_body, email_html)

class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    @method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True))
    def post(self, request, *args, **kwargs):
        # Rate limit por tenant
        tenant_subdomain = get_explicit_tenant_input(request.data)
        email = (request.data.get('email') or '').strip().lower()
        ip_address = get_client_ip(request)
        user_for_lockout = None

        if email:
            if tenant_subdomain:
                tenant_for_lockout = Tenant.objects.filter(subdomain=tenant_subdomain).first()
                if tenant_for_lockout:
                    user_for_lockout = User.objects.filter(email=email, tenant=tenant_for_lockout).first()
            else:
                user_for_lockout = User.objects.filter(
                    email=email,
                    is_superuser=True,
                    tenant__isnull=True
                ).first()

        if is_login_locked_out(user=user_for_lockout, ip_address=ip_address):
            return Response({"detail": get_login_lockout_message()}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        if tenant_subdomain:
            from django_ratelimit.core import is_ratelimited
            if is_ratelimited(request, group='tenant_login', key=lambda r, g: tenant_subdomain, rate='20/m', method='POST'):
                return Response({"detail": "Demasiados intentos de login para este tenant."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            if tenant_subdomain:
                try:
                    tenant = Tenant.objects.get(subdomain=tenant_subdomain)
                    user = User.objects.filter(email=email, tenant=tenant).first()
                except (Tenant.DoesNotExist, User.DoesNotExist):
                    user = None
            else:
                user = User.objects.filter(
                    email=email,
                    is_superuser=True,
                    tenant__isnull=True
                ).first()
            
            safe_create_login_audit(
                user=user,
                request=request,
                successful=False,
                message=f"Credenciales inválidas - Tenant: {tenant_subdomain or 'unknown'}"
            )
            raise
        
        user = serializer.validated_data['user']
        tenant = serializer.validated_data['tenant']

        user_role_api = get_effective_role_api(user, tenant=tenant)
        if not tenant and user_role_api != 'SUPER_ADMIN':
            return Response({"detail": "Usuario sin tenant asignado. Contacte al administrador."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            LoginAudit.objects.create(
                user=user,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request)[:255],
                successful=False,
                message="Cuenta inactiva"[:255],
                timestamp=now()
            )
            return Response({"detail": "Cuenta inactiva. Contacte al administrador."}, status=status.HTTP_403_FORBIDDEN)

        if is_mfa_globally_enabled() and user.mfa_enabled:
            tenant_data = {"id": tenant.id, "subdomain": tenant.subdomain} if tenant else None
            return Response({
                "detail": "Se requiere verificación MFA.",
                "email": user.email,
                "tenant": tenant_data
            }, status=status.HTTP_200_OK)

        refresh, access = issue_refresh_for_user(user, tenant)
        access_token = str(access)
        refresh_token = str(refresh)
        jti = get_client_jti(access_token)

        ActiveSession.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)[:255],
            token_jti=jti,
            refresh_token=refresh_token,
            is_active=True,
            tenant=tenant
        )

        AccessLog.objects.create(
            user=user,
            event_type='LOGIN',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)[:255],
            timestamp=now()
        )
        LoginAudit.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)[:255],
            successful=True,
            message="Inicio de sesión exitoso"[:255],
            timestamp=now()
        )

        user_role = get_effective_role_api(user, tenant=tenant)
        
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
                            user_agent=get_user_agent(request)[:255],
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
                user_agent=get_user_agent(request)[:255],
                timestamp=now()
            )

            subject = "Cambio de contraseña exitoso"
            text_body = f"Hola {user.full_name}, tu contraseña ha sido cambiada exitosamente."
            html_body = _build_branded_email_html(
                user=user,
                title=subject,
                message_html=(
                    f"<p>Hola {escape(user.full_name or user.email)},</p>"
                    "<p>Tu contraseña fue actualizada correctamente.</p>"
                ),
                request=request
            )
            _deliver_user_email(user, subject, text_body, html_body)

            return Response({"detail": "Contraseña actualizada correctamente."})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = (serializer.validated_data.get('email') or '').strip().lower()
        tenant_subdomain = get_explicit_tenant_input(serializer.validated_data)
        try:
            user = None
            if tenant_subdomain:
                tenant = Tenant.objects.filter(
                    subdomain=tenant_subdomain,
                    is_active=True,
                    deleted_at__isnull=True
                ).first()
                if tenant:
                    user = User.objects.filter(email=email, tenant=tenant).first()
            else:
                candidates = list(User.objects.filter(email=email).select_related('tenant'))
                if len(candidates) > 1:
                    return Response(
                        {
                            "detail": "Este correo pertenece a varios tenants. Indica el subdominio para continuar.",
                            "code": "tenant_required"
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if candidates:
                    user = candidates[0]

            if not user:
                return Response({"detail": "Correo enviado si el usuario existe."}, status=status.HTTP_200_OK)

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            
            # Use environment variable for frontend URL
            frontend_url = settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'http://localhost:4200'
            reset_url = f"{frontend_url}/auth/reset-password/{uid}/{token}"

            AccessLog.objects.create(
                user=user,
                event_type='PASSWORD_RESET_REQUEST',
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request)[:255],
                timestamp=now()
            )

            if settings.DEBUG:
                logger.debug(
                    "Password reset link generated for user_id=%s reset_url=%s",
                    user.id,
                    reset_url,
                )
            
            subject = "Restablecer contraseña"
            text_body = f"Hola {user.full_name}, para restablecer tu contraseña haz clic en el siguiente enlace:\n{reset_url}"
            html_body = _build_branded_email_html(
                user=user,
                title=subject,
                message_html=(
                    f"<p>Hola {escape(user.full_name or user.email)},</p>"
                    "<p>Recibimos una solicitud para restablecer tu contraseña.</p>"
                ),
                cta_url=reset_url,
                cta_label="Restablecer contraseña",
                request=request
            )
            _deliver_user_email(user, subject, text_body, html_body)

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
            user_agent=get_user_agent(request)[:255],
            timestamp=now()
        )

        subject = "Contraseña restablecida"
        text_body = f"Hola {user.full_name}, tu contraseña ha sido restablecida exitosamente."
        html_body = _build_branded_email_html(
            user=user,
            title=subject,
            message_html=(
                f"<p>Hola {escape(user.full_name or user.email)},</p>"
                "<p>Tu contraseña fue restablecida exitosamente.</p>"
            ),
            request=request
        )
        _deliver_user_email(user, subject, text_body, html_body)

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
                user_agent=get_user_agent(request)[:255],
                timestamp=now()
            )
            return self.get_paginated_response(serializer.data)  # Devolver respuesta paginada
        serializer = self.get_serializer(queryset, many=True)
        AccessLog.objects.create(
            user=request.user,
            event_type='ACTIVE_SESSIONS_VIEW',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)[:255],
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
                user_agent=get_user_agent(request)[:255],
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
                user_agent=get_user_agent(request)[:255],
                timestamp=now()
            )
            return Response({"detail": "Correo verificado exitosamente."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)

class MFASetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not is_mfa_globally_enabled():
            return Response({"error": "MFA está deshabilitado por configuración del sistema."}, status=status.HTTP_400_BAD_REQUEST)
        if user.mfa_enabled:
            return Response({"error": "MFA ya está habilitado."}, status=status.HTTP_400_BAD_REQUEST)

        secret = user.mfa_secret or pyotp.random_base32()
        if user.mfa_secret != secret:
            user.mfa_secret = secret
            user.save(update_fields=['mfa_secret'])

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
            user_agent=get_user_agent(request)[:255],
            timestamp=now()
        )
        return Response({"qr_code": qr_code, "secret": secret})

class MFAVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not is_mfa_globally_enabled():
            return Response({"error": "MFA está deshabilitado por configuración del sistema."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = MFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        totp = pyotp.TOTP(user.mfa_secret)
        if totp.verify(serializer.validated_data['code'], valid_window=2):
            user.mfa_enabled = True
            user.save()
            AccessLog.objects.create(
                user=user,
                event_type='MFA_VERIFIED',
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request)[:255],
                timestamp=now()
            )
            return Response({"detail": "MFA verificado y habilitado."})
        return Response({"error": "Código inválido."}, status=status.HTTP_400_BAD_REQUEST)


class MFADisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.mfa_enabled or not user.mfa_secret:
            return Response({"error": "MFA no está habilitado."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        totp = pyotp.TOTP(user.mfa_secret)

        if not totp.verify(serializer.validated_data['code'], valid_window=2):
            return Response({"error": "Código inválido."}, status=status.HTTP_400_BAD_REQUEST)

        user.mfa_enabled = False
        user.mfa_secret = None
        user.save(update_fields=['mfa_enabled', 'mfa_secret'])

        AccessLog.objects.create(
            user=user,
            event_type='MFA_DISABLED',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)[:255],
            timestamp=now()
        )
        return Response({"detail": "MFA deshabilitado correctamente."})

class MFALoginVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not is_mfa_globally_enabled():
            return Response({"error": "MFA está deshabilitado por configuración del sistema."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = MFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = request.data.get('email')
        tenant_subdomain = get_explicit_tenant_input(request.data)
        

        if not tenant_subdomain:
            return Response({"error": "Tenant requerido."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            tenant = Tenant.objects.get(subdomain=tenant_subdomain)
            user = User.objects.get(email=email, tenant=tenant)
        except (Tenant.DoesNotExist, User.DoesNotExist):
            return Response({"error": "Usuario o tenant no encontrado."}, status=status.HTTP_400_BAD_REQUEST)

        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(serializer.validated_data['code'], valid_window=2):
            LoginAudit.objects.create(
                user=user,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request)[:255],
                successful=False,
                message="Código MFA inválido"[:255],
                timestamp=now()
            )
            return Response({"error": "Código MFA inválido."}, status=status.HTTP_400_BAD_REQUEST)

        if is_login_locked_out(user=user, ip_address=get_client_ip(request)):
            return Response({"error": get_login_lockout_message()}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        refresh, access = issue_refresh_for_user(user, tenant)
        access_token = str(access)
        refresh_token = str(refresh)
        jti = get_client_jti(access_token)

        ActiveSession.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)[:255],
            token_jti=jti,
            refresh_token=refresh_token,
            is_active=True,
            tenant=tenant
        )

        AccessLog.objects.create(
            user=user,
            event_type='LOGIN_MFA',
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)[:255],
            timestamp=now()
        )
        LoginAudit.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)[:255],
            successful=True,
            message="Inicio de sesión con MFA exitoso"[:255],
            timestamp=now()
        )

        user_role = get_effective_role_api(user, tenant=tenant)

        response_data = {
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user_role,
            },
            'access': access_token,
            'refresh': refresh_token,
            'message': 'Inicio de sesión con MFA exitoso'
        }

        if tenant:
            response_data['tenant'] = {
                'id': tenant.id,
                'name': tenant.name,
                'subdomain': tenant.subdomain,
            }

        response = Response(response_data)

        return set_auth_cookies(
            response,
            access_token=access_token,
            refresh_token=refresh_token,
            access_max_age=get_jwt_expiry_minutes() * 60,
            refresh_max_age=24 * 60 * 60,
            tenant_id=tenant.id if tenant else None,
        )



class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.none()  # Seguro por defecto
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'auth_api.view_user',
        'retrieve': 'auth_api.view_user',
        'create': 'auth_api.add_user',
        'update': 'auth_api.change_user',
        'partial_update': 'auth_api.change_user',
        'destroy': 'auth_api.delete_user',
        'available_for_employee': 'auth_api.view_user',
        'bulk_delete': 'auth_api.delete_user',
        'upload_avatar': 'auth_api.change_user',
    }
    serializer_class = UserListSerializer
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def _get_request_tenant(self):
        tenant = getattr(self.request, 'tenant', None)
        if tenant is not None:
            return tenant

        user = getattr(self.request, 'user', None)
        if getattr(user, 'is_authenticated', False):
            return getattr(user, 'tenant', None)

        return None

    def _is_tenant_admin_or_superuser(self, request) -> bool:
        """Solo SuperAdmin o Client-Admin pueden gestionar usuarios."""
        return get_effective_role_name(
            request.user,
            tenant=self._get_request_tenant(),
        ) in {'SuperAdmin', 'Client-Admin'}
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy to add logging and proper deletion"""
        if not self._is_tenant_admin_or_superuser(request):
            return Response(
                {'error': 'Solo Client-Admin puede eliminar usuarios'},
                status=status.HTTP_403_FORBIDDEN
            )

        instance = self.get_object()
        logger.info("Attempting to delete user_id=%s by actor_id=%s", instance.id, request.user.id)
        
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
                user_agent=get_user_agent(request)[:255],
                timestamp=now()
            )
            
            # Perform the deletion
            self.perform_destroy(instance)
            logger.info("User deleted successfully user_id=%s", instance.id)
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.exception("Error deleting user_id=%s", instance.id)
            return Response({
                'error': f'Failed to delete user: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    def perform_destroy(self, instance):
        """Actually delete the user instance"""
        instance.delete()

    def get_object(self):
        """
        Resolve detail objects without DRF filter backends interfering with
        DELETE/PUT lookups. This keeps the same visibility rules as get_queryset
        while avoiding false 404s on existing users.
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs.get(lookup_url_kwarg)
        filter_kwargs = {self.lookup_field: lookup_value}

        obj = self.get_queryset().filter(**filter_kwargs).first()
        if obj is None:
            logger.warning(
                "User lookup failed user_id=%s actor_id=%s actor_superuser=%s actor_tenant_id=%s request_tenant_id=%s",
                lookup_value,
                getattr(self.request.user, 'id', None),
                getattr(self.request.user, 'is_superuser', False),
                getattr(getattr(self.request.user, 'tenant', None), 'id', None),
                getattr(getattr(self.request, 'tenant', None), 'id', None),
            )
            raise NotFound("Usuario no encontrado.")

        self.check_object_permissions(self.request, obj)
        return obj
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return EmployeeUserSerializer
        return UserListSerializer

    def create(self, request, *args, **kwargs):
        if not self._is_tenant_admin_or_superuser(request):
            return Response(
                {'error': 'Solo Client-Admin puede crear usuarios'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check user limits for non-superadmin
        if not request.user.is_superuser and request.user.tenant:
            tenant = request.user.tenant
            if not tenant.can_add_user():
                upgrade_result = maybe_auto_upgrade_user_limit(tenant, changed_by=request.user)
                tenant.refresh_from_db(fields=['plan_type', 'subscription_plan', 'max_employees', 'max_users', 'settings', 'updated_at'])
            if not tenant.can_add_user():
                error_message = 'User limit reached for your plan'
                if upgrade_result.get('reason') == 'no_higher_plan':
                    error_message = 'User limit reached and there is no higher plan available for automatic upgrade'
                return Response({
                    'error': error_message,
                    'current': tenant.get_user_usage()['current'],
                    'limit': tenant.max_users
                }, status=status.HTTP_403_FORBIDDEN)
        
        # ✅ VALIDACIÓN DE JERARQUÍA DE ROLES
        requested_role = request.data.get('role')
        actor_role = get_effective_role_name(request.user, tenant=self._get_request_tenant()) or 'Client-Staff'
        if requested_role:
            is_valid, error_msg = validate_role_assignment(
                creator_role=actor_role,
                target_role=requested_role,
                creator_is_superuser=request.user.is_superuser
            )
            if not is_valid:
                return Response({
                    'error': error_msg,
                    'your_role': actor_role,
                    'allowed_roles': get_allowed_roles(actor_role, request.user.is_superuser)
                }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = serializer.save()
            
            # FORZAR asignación de tenant si no se asignó
            if not user.tenant and not self.request.user.is_superuser:
                if hasattr(self.request, 'tenant') and self.request.tenant:
                    user.tenant = self.request.tenant
                    user.save()
            
            # Asignar rol si se especifica
            if requested_role:
                user.role = requested_role
                user.save()
                
                # Crear UserRole si no es SuperAdmin
                if requested_role != 'SuperAdmin':
                    try:
                        role = Role.objects.get(name=requested_role)
                        UserRole.objects.get_or_create(
                            user=user,
                            role=role,
                            tenant=user.tenant
                        )
                    except Role.DoesNotExist:
                        pass
            
            # Retornar datos completos del usuario
            response_serializer = UserListSerializer(user)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        if not self._is_tenant_admin_or_superuser(request):
            return Response(
                {'error': 'Solo Client-Admin puede modificar usuarios'},
                status=status.HTTP_403_FORBIDDEN
            )

        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        is_self_update = instance.id == request.user.id

        # Permitir auto-edición básica del propio perfil sin validación jerárquica de roles.
        if is_self_update:
            allowed_self_fields = {'full_name', 'email', 'phone'}
            requested_fields = set(request.data.keys())
            blocked_fields = requested_fields - allowed_self_fields
            if blocked_fields:
                return Response(
                    {
                        'error': 'No puedes modificar estos campos en tu propio perfil',
                        'blocked_fields': sorted(list(blocked_fields))
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            try:
                serializer.is_valid(raise_exception=True)
                user = serializer.save()
                return Response(UserListSerializer(user).data)
            except ValidationError as e:
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        # ✅ VALIDAR QUE PUEDE MODIFICAR ESTE USUARIO
        actor_role = get_effective_role_name(request.user, tenant=self._get_request_tenant()) or 'Client-Staff'
        target_role = get_effective_role_name(instance, tenant=instance.tenant) or 'Client-Staff'
        can_modify, error_msg = can_modify_user(
            modifier_role=actor_role,
            target_user_role=target_role,
            modifier_is_superuser=request.user.is_superuser
        )
        if not can_modify:
            return Response({'error': error_msg}, status=status.HTTP_403_FORBIDDEN)
        
        # ✅ VALIDAR CAMBIO DE ROL SI SE ESPECIFICA
        if 'role' in request.data:
            new_role = request.data.get('role')
            is_valid, error_msg = validate_role_assignment(
                creator_role=actor_role,
                target_role=new_role,
                creator_is_superuser=request.user.is_superuser
            )
            if not is_valid:
                return Response({
                    'error': error_msg,
                    'your_role': actor_role,
                    'allowed_roles': get_allowed_roles(actor_role, request.user.is_superuser)
                }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Actualizar rol si se especifica
            if 'role' in request.data:
                role_name = request.data.get('role')
                user.role = role_name
                user.save()
                
                # Manejar UserRole si no es SuperAdmin
                if role_name and role_name != 'SuperAdmin':
                    UserRole.objects.filter(user=user).delete()
                    try:
                        role = Role.objects.get(name=role_name)
                        UserRole.objects.get_or_create(
                            user=user,
                            role=role,
                            tenant=user.tenant
                        )
                    except Role.DoesNotExist:
                        pass
            
            # Retornar datos completos del usuario
            response_serializer = UserListSerializer(user)
            return Response(response_serializer.data)
            
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        user = self.request.user
        
        # SuperAdmin: acceso total
        if user.is_superuser:
            tenant_id = self.request.query_params.get('tenant')
            queryset = User.objects.select_related('tenant').all()
            if tenant_id:
                return queryset.filter(tenant_id=tenant_id)
            return queryset
        
        # Usuario sin tenant: sin acceso
        tenant = self._get_request_tenant()
        if not tenant:
            return User.objects.none()
        
        # Filtrar por tenant del request o del usuario autenticado como fallback
        return User.objects.select_related('tenant').filter(tenant=tenant)

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

    @action(detail=False, methods=['post'], url_path='me/avatar', permission_classes=[IsAuthenticated])
    def upload_avatar(self, request):
        """Subir avatar del usuario autenticado."""
        if 'avatar' not in request.FILES:
            return Response({'error': 'No avatar file provided'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.avatar = request.FILES['avatar']
        user.save()

        return Response({
            'avatar_url': user.avatar.url if user.avatar else None,
            'message': 'Avatar actualizado correctamente'
        })
    
    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """Bulk delete users"""
        if not self._is_tenant_admin_or_superuser(request):
            return Response(
                {'error': 'Solo Client-Admin puede eliminar usuarios'},
                status=status.HTTP_403_FORBIDDEN
            )

        user_ids = request.data.get('user_ids', [])
        users = self.get_queryset().filter(id__in=user_ids)
        
        # Prevent deleting last superuser
        if users.filter(is_superuser=True).exists():
            remaining_superusers = User.objects.filter(is_superuser=True).exclude(id__in=user_ids).count()
            if remaining_superusers == 0:
                return Response({
                    'error': 'Cannot delete all superusers'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        count = users.count()
        users.delete()
        return Response({'deleted': count})


class VerifyAuthView(APIView):
    """Verificar autenticación con cookies httpOnly"""
    authentication_classes = [DualJWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'authenticated': True,
            'user': {
                'id': request.user.id,
                'email': request.user.email,
                'role': get_effective_role_api(request.user, tenant=getattr(request, 'tenant', None))
            }
        })
