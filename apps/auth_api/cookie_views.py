from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django_ratelimit.core import is_ratelimited
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer
from .models import ActiveSession, AccessLog, LoginAudit
from .utils import get_client_ip, get_user_agent, get_client_jti
from django.utils.timezone import now
from django.contrib.auth import get_user_model
from apps.tenants_api.models import Tenant

User = get_user_model()


class CookieLoginThrottle(AnonRateThrottle):
    scope = 'login'


class CookieRefreshThrottle(AnonRateThrottle):
    scope = 'login'


def _jwt_cookie_max_age(setting_name: str) -> int:
    lifetime = settings.SIMPLE_JWT.get(setting_name)
    if lifetime is None:
        return 0

    return max(0, int(lifetime.total_seconds()))


def _safe_user_agent(request) -> str:
    return (get_user_agent(request) or '')[:255]


def _create_login_audit(user, request, successful: bool, message: str) -> None:
    LoginAudit.objects.create(
        user=user,
        ip_address=get_client_ip(request),
        user_agent=_safe_user_agent(request),
        successful=successful,
        message=(message or '')[:255],
        timestamp=now()
    )


class CookieLoginView(APIView):
    """
    Vista de login que establece JWT tokens en httpOnly cookies
    Ruta: /api/auth/cookie-login/
    """
    permission_classes = [AllowAny]
    throttle_classes = [CookieLoginThrottle]
    
    @method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True))
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        tenant_subdomain = request.META.get('HTTP_HOST', '').split('.')[0] if '.' in request.META.get('HTTP_HOST', '') else request.data.get('tenant_subdomain')
        if tenant_subdomain and is_ratelimited(request, group='tenant_login', key=lambda r: tenant_subdomain, rate='20/m', method='POST'):
            return Response({"detail": "Demasiados intentos de login para este tenant."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            email = (request.data.get('email') or '').strip().lower()
            user = None

            if email:
                try:
                    if tenant_subdomain:
                        tenant = Tenant.objects.filter(subdomain=tenant_subdomain).first()
                        if tenant:
                            user = User.objects.filter(email=email, tenant=tenant).first()
                    else:
                        user = User.objects.filter(email=email).first()
                except Exception:
                    user = None

            _create_login_audit(
                user=user,
                request=request,
                successful=False,
                message=f"Credenciales inválidas - Cookie login - Tenant: {tenant_subdomain or 'unknown'}"
            )
            raise
        
        user = serializer.validated_data['user']
        tenant = serializer.validated_data['tenant']

        if user.mfa_enabled:
            tenant_data = {
                'id': tenant.id,
                'subdomain': tenant.subdomain,
            } if tenant else None

            return Response({
                'detail': 'Se requiere verificación MFA.',
                'email': user.email,
                'tenant': tenant_data,
                'requires_mfa': True,
            }, status=status.HTTP_200_OK)
        
        # Generar tokens
        refresh = RefreshToken.for_user(user)
        if tenant:
            refresh['tenant_id'] = tenant.id
            refresh['tenant_subdomain'] = tenant.subdomain
            
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        jti = get_client_jti(access_token)
        
        # Crear sesión activa
        ActiveSession.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=_safe_user_agent(request),
            token_jti=jti,
            refresh_token=refresh_token,
            is_active=True,
            tenant=tenant
        )
        
        # Logs de auditoría
        AccessLog.objects.create(
            user=user,
            event_type='LOGIN',
            ip_address=get_client_ip(request),
            user_agent=_safe_user_agent(request),
            timestamp=now()
        )
        
        _create_login_audit(
            user=user,
            successful=True,
            request=request,
            message="Login con cookies exitoso"
        )
        
        # Respuesta con datos del usuario
        user_role = (user.role or 'Client-Staff').upper().replace('-', '_')

        response_data = {
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'phone': user.phone,
                'role': user_role,
                'is_active': user.is_active,
                'date_joined': user.date_joined,
                'avatar_url': user.avatar.url if user.avatar else None,
            },
            'message': 'Login exitoso con cookies'
        }
        
        if tenant:
            response_data['tenant'] = {
                'id': tenant.id,
                'name': tenant.name,
                'subdomain': tenant.subdomain,
            }
        
        response = Response(response_data, status=status.HTTP_200_OK)
        
        # Establecer cookies httpOnly
        response.set_cookie(
            'access_token',
            value=access_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Strict',
            max_age=_jwt_cookie_max_age('ACCESS_TOKEN_LIFETIME'),
            path='/'
        )
        
        response.set_cookie(
            'refresh_token',
            value=refresh_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Strict',
            max_age=_jwt_cookie_max_age('REFRESH_TOKEN_LIFETIME'),
            path='/'
        )
        
        if tenant:
            response.set_cookie(
                'tenant_id', 
                str(tenant.id), 
                httponly=False,  # Frontend necesita leer esto
                secure=not settings.DEBUG, 
                samesite='Strict'
            )
        
        return response


class CookieLogoutView(APIView):
    """
    Vista de logout que limpia cookies httpOnly
    Ruta: /api/auth/cookie-logout/
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                
                # Expirar sesión activa
                try:
                    session = ActiveSession.objects.get(refresh_token=refresh_token)
                    session.expire_session()
                    
                    # Log de logout si tenemos usuario
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
                    
            except Exception:
                pass  # Token inválido, pero seguimos con logout
        
        response = Response({
            "detail": "Logout exitoso con cookies"
        }, status=status.HTTP_200_OK)
        
        # Limpiar todas las cookies
        response.delete_cookie('access_token', path='/')
        response.delete_cookie('refresh_token', path='/')
        response.delete_cookie('tenant_id', path='/')
        
        return response


class CookieRefreshView(APIView):
    """
    Vista para refrescar tokens usando cookies
    Ruta: /api/auth/cookie-refresh/
    """
    permission_classes = [AllowAny]
    throttle_classes = [CookieRefreshThrottle]
    
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        
        if not refresh_token:
            return Response({
                'error': 'No refresh token found'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        try:
            token = RefreshToken(refresh_token)
            new_access_token = str(token.access_token)
            
            response = Response({
                'message': 'Token refreshed successfully'
            }, status=status.HTTP_200_OK)
            
            # Establecer nuevo access token
            response.set_cookie(
                'access_token',
                value=new_access_token,
                httponly=True,
                secure=not settings.DEBUG,
                samesite='Strict',
                max_age=_jwt_cookie_max_age('ACCESS_TOKEN_LIFETIME'),
                path='/'
            )
            
            return response
            
        except Exception as e:
            return Response({
                'error': 'Invalid refresh token'
            }, status=status.HTTP_401_UNAUTHORIZED)
