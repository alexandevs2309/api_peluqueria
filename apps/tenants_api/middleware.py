from django.http import JsonResponse, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from .models import Tenant
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings

from django.contrib.gis.geoip2 import GeoIP2
from apps.auth_api.utils import get_client_ip

class TenantMiddleware(MiddlewareMixin):
    """
    Middleware para manejar multitenancy basado en JWT claims o usuario autenticado
    """
    
    def process_request(self, request):
        # Excluir admin de Django
        if request.path.startswith('/admin/'):
            return None
        
        # Solo aplicar a rutas API
        if not request.path.startswith('/api/'):
            return None
        
        # Rutas exentas
        exempt_paths = [
            '/api/auth/',
            '/api/schema/',
            '/api/docs/',
            '/api/healthz/',
            '/api/system-settings/',
            '/api/subscriptions/plans/',  # Allow subscription plans access
            '/api/subscriptions/register/',  # Allow registration
            '/api/settings/contact/',  # Allow contact forms
        ]
        for exempt_path in exempt_paths:
            if request.path.startswith(exempt_path):
                return None
        
        # Intentar obtener tenant desde JWT claims
        try:
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                token_str = auth_header.split(' ')[1]
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(token_str)
                tenant_id = validated_token.get('tenant_id')
                if tenant_id:
                    tenant = Tenant.objects.get(id=tenant_id)
                    request.tenant = tenant
                else:
                    request.tenant = None
            else:
                request.tenant = None
        except (InvalidToken, TokenError, Tenant.DoesNotExist):
            return HttpResponseForbidden("Token o tenant inválido.")
        
        # Si no tenant desde JWT, fallback a usuario
        if not request.tenant:
            if hasattr(request, 'user') and request.user.is_authenticated:
                if request.user.roles.filter(name='Super-Admin').exists():
                    request.tenant = None
                elif hasattr(request.user, 'tenant') and request.user.tenant:
                    request.tenant = request.user.tenant
                else:
                    if request.path.startswith('/api/subscriptions/me/'):
                        request.tenant = None
                    else:
                        return JsonResponse({
                            'error': 'Usuario sin tenant asignado',
                            'code': 'NO_TENANT'
                        }, status=403)
            else:
                request.tenant = None
        
        # Geolock opcional
        if getattr(settings, 'GEO_LOCK_ENABLED', False) and request.tenant and request.tenant.country:
            client_ip = get_client_ip(request)
            try:
                geo = GeoIP2()
                country = geo.country(client_ip)['country_code']
                if country != request.tenant.country:
                    return JsonResponse({
                        'error': 'Geographic access denied',
                        'code': 'GEO_BLOCKED',
                        'allowed_country': request.tenant.country,
                        'detected_country': country
                    }, status=403)
            except Exception as e:
                # Log error pero permitir acceso en caso de fallo de geolocalización
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f'GeoIP error for IP {client_ip}: {str(e)}')
                pass
        
        return None
