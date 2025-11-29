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
            '/api/subscriptions/register-with-plan/',  # Allow registration with plan
            '/api/settings/contact/',  # Allow contact forms
            '/api/settings/admin/',  # Allow super admin endpoints
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
                # Permitir acceso a super admins
                if (request.user.is_superuser or 
                    (hasattr(request.user, 'role') and request.user.role == 'super_admin')):
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
        
        # Verificar y manejar trial expirado
        if request.tenant:
            request.tenant.check_and_suspend_expired_trial()
            access_level = request.tenant.get_access_level()
            
            if access_level == 'blocked':
                return JsonResponse({
                    'error': 'Access blocked',
                    'code': 'SUBSCRIPTION_REQUIRED',
                    'message': 'Your trial has expired. Please subscribe to continue using the service.',
                    'upgrade_url': '/subscriptions/upgrade/'
                }, status=402)
            elif access_level == 'grace':
                # Permitir acceso pero agregar header de advertencia
                response = None
                request.grace_period = True
            
            # Enviar notificaciones de trial
            self.check_trial_notifications(request.tenant)
        
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
    
    def check_trial_notifications(self, tenant):
        """Verificar y enviar notificaciones de trial"""
        if tenant.subscription_status != 'trial':
            return
            
        # Notificación 3 días antes
        if tenant.should_send_trial_notification(3):
            self.send_trial_notification(tenant, 3)
            tenant.mark_notification_sent(3)
        
        # Notificación 1 día antes
        elif tenant.should_send_trial_notification(1):
            self.send_trial_notification(tenant, 1)
            tenant.mark_notification_sent(1)
    
    def send_trial_notification(self, tenant, days_left):
        """Enviar notificación de trial"""
        import logging
        logger = logging.getLogger(__name__)
        
        if days_left > 0:
            logger.info(f"TRIAL WARNING: {tenant.name} has {days_left} days left")
        else:
            days_since_expiry = (timezone.now().date() - tenant.trial_end_date).days if tenant.trial_end_date else 0
            if days_since_expiry <= 3:
                logger.info(f"GRACE PERIOD: {tenant.name} in grace period, {3 - days_since_expiry} days left")
        # TODO: Implementar envío real de email/SMS
