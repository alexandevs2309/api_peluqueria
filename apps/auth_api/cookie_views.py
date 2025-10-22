from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer
from .models import ActiveSession, AccessLog, LoginAudit
from .utils import get_client_ip, get_user_agent, get_client_jti
from django.utils.timezone import now


class CookieLoginView(APIView):
    """
    Vista de login que establece JWT tokens en httpOnly cookies
    Ruta: /api/auth/cookie-login/
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        tenant = serializer.validated_data['tenant']
        
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
            user_agent=get_user_agent(request),
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
            user_agent=get_user_agent(request),
            timestamp=now()
        )
        
        LoginAudit.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            successful=True,
            message="Login con cookies exitoso",
            timestamp=now()
        )
        
        # Respuesta con datos del usuario
        response_data = {
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role or 'ClientStaff',
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
            max_age=8 * 60 * 60,  # 8 horas
            path='/'
        )
        
        response.set_cookie(
            'refresh_token',
            value=refresh_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Strict',
            max_age=30 * 24 * 60 * 60,  # 30 días
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
                max_age=8 * 60 * 60,  # 8 horas
                path='/'
            )
            
            return response
            
        except Exception as e:
            return Response({
                'error': 'Invalid refresh token'
            }, status=status.HTTP_401_UNAUTHORIZED)