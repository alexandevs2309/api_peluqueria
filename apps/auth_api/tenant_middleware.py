from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
import jwt
from django.conf import settings

User = get_user_model()

class TenantIsolationMiddleware(MiddlewareMixin):
    """
    Middleware que valida que el usuario solo acceda a recursos de su tenant
    """
    
    def process_request(self, request):
        # Rutas que no requieren validación de tenant
        exempt_paths = [
            '/api/auth/login/',
            '/api/auth/register/',
            '/api/subscriptions/register/',
            '/api/auth/password-reset/',
            '/api/auth/verify-email/',
            '/admin/',
            '/api/docs/',
            '/api/schema/',
        ]
        
        # Verificar si la ruta está exenta
        if any(request.path.startswith(path) for path in exempt_paths):
            return None
            
        # Solo validar requests autenticados
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
            
        # Superusuarios pueden acceder a todo
        if request.user.is_superuser:
            return None
            
        # Obtener token del header Authorization
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
            
        try:
            token = auth_header.split(' ')[1]
            decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            token_tenant_id = decoded_token.get('tenant_id')
            
            # Validar que el tenant del token coincida con el del usuario
            if not request.user.tenant:
                return JsonResponse({
                    'error': 'Usuario sin tenant asignado'
                }, status=403)
                
            if token_tenant_id != request.user.tenant_id:
                return JsonResponse({
                    'error': 'Acceso denegado: tenant incorrecto'
                }, status=403)
                
        except (jwt.InvalidTokenError, jwt.DecodeError, KeyError):
            # Si no se puede decodificar el token, continuar
            # (otros middlewares manejarán la autenticación)
            pass
            
        return None