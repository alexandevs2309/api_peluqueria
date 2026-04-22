from django.http import JsonResponse, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from .models import Tenant
from .subscription_lifecycle import sync_subscription_state
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings
import logging

from django.contrib.gis.geoip2 import GeoIP2
from apps.auth_api.utils import get_client_ip

logger = logging.getLogger(__name__)

class TenantMiddleware(MiddlewareMixin):
    """
    Middleware para manejar multitenancy basado en JWT claims o usuario autenticado
    """

    @staticmethod
    def _is_superadmin(user) -> bool:
        if not getattr(user, 'is_authenticated', False):
            return False
        return bool(
            getattr(user, 'is_superuser', False) or
            getattr(user, 'role', '') == 'super_admin' or
            getattr(user, 'role', '') == 'SuperAdmin'
        )

    @staticmethod
    def _inactive_tenant_response(tenant=None):
        message = 'Esta cuenta empresarial se encuentra desactivada o suspendida. Contacte al soporte o al administrador del SaaS.'
        reason = 'tenant_inactive'

        if tenant is not None:
            if getattr(tenant, 'deleted_at', None) is not None:
                reason = 'tenant_deleted'
                message = 'Esta cuenta empresarial fue desactivada. Contacte al soporte o al administrador del SaaS.'
            elif getattr(tenant, 'subscription_status', None) == 'suspended':
                reason = 'tenant_suspended'
                message = 'La cuenta de su empresa esta suspendida. Contacte al soporte o al administrador del SaaS.'
            elif getattr(tenant, 'subscription_status', None) == 'archived':
                reason = 'tenant_archived'
                message = 'La cuenta de su empresa fue archivada por falta prolongada de pago. Contacte al soporte.'
            elif getattr(tenant, 'subscription_status', None) == 'past_due':
                reason = 'tenant_past_due'
                message = 'La cuenta de su empresa tiene pagos pendientes. Regularice su suscripcion.'
            elif getattr(tenant, 'is_trial_expired', None) and tenant.is_trial_expired():
                reason = 'trial_expired'
                message = 'El periodo de prueba de su empresa ha expirado. Contacte al soporte o al administrador del SaaS.'
            elif getattr(tenant, 'is_paid_access_expired', None) and tenant.is_paid_access_expired():
                reason = 'paid_access_expired'
                message = 'El acceso de pago de su empresa ha expirado. Contacte al soporte o al administrador del SaaS.'

        return JsonResponse({
            'error': 'TENANT_INACTIVE',
            'code': 'TENANT_INACTIVE',
            'reason': reason,
            'message': message,
            'tenant_id': getattr(tenant, 'id', None),
            'tenant_subdomain': getattr(tenant, 'subdomain', None),
            'support_email': 'support@barbershop.com'
        }, status=403)
    
    def process_request(self, request):
        # Excluir admin de Django
        if request.path.startswith('/admin/'):
            return None
        
        # Solo aplicar a rutas API
        if not request.path.startswith('/api/'):
            return None
        
        # Rutas exentas (solo públicas)
        exempt_paths = [
            '/api/auth/login/',
            '/api/auth/cookie-login/',
            '/api/auth/cookie-logout/',
            '/api/auth/cookie-refresh/',
            '/api/auth/mfa/login-verify/',
            '/api/auth/register/',
            '/api/auth/password-reset/',
            '/api/healthz/',
            '/api/subscriptions/plans/',  # Solo lectura
            '/api/subscriptions/register/',
            '/api/subscriptions/register-with-plan/',
            '/api/settings/contact/',  # Formulario público
        ]
        if settings.DEBUG:
            exempt_paths.extend(['/api/schema/', '/api/docs/'])
        for exempt_path in exempt_paths:
            if request.path.startswith(exempt_path):
                return None
        
        # ✅ AUTENTICAR USUARIO DESDE COOKIES PRIMERO
        if not (hasattr(request, 'user') and request.user.is_authenticated):
            from apps.auth_api.authentication import CookieJWTAuthentication
            try:
                auth_result = CookieJWTAuthentication().authenticate(request)
                if auth_result:
                    request.user, _ = auth_result
            except Exception:
                pass
        
        # Rutas admin requieren superuser
        admin_paths = [
            '/api/settings/admin/',
            '/api/system-settings/',
            '/api/tenants/subscription-status/',
        ]
        for admin_path in admin_paths:
            if request.path.startswith(admin_path):
                if not (hasattr(request, 'user') and request.user.is_authenticated and request.user.is_superuser):
                    return JsonResponse({
                        'error': 'Forbidden',
                        'code': 'SUPERUSER_REQUIRED'
                    }, status=403)

        # El dueno del SaaS no debe depender de tenant ni de claims stale en tokens.
        if self._is_superadmin(getattr(request, 'user', None)):
            request.tenant = None
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
                    try:
                        tenant = Tenant.objects.get(
                            id=tenant_id,
                            deleted_at__isnull=True,
                            is_active=True
                        )
                        request.tenant = tenant
                        
                        # ✅ VALIDACIÓN DEFENSIVA: JWT tenant debe coincidir con user.tenant
                        if hasattr(request, 'user') and request.user.is_authenticated:
                            if not request.user.is_superuser and request.user.tenant_id != tenant_id:
                                return JsonResponse({
                                    'error': 'TENANT_MISMATCH',
                                    'code': 'TENANT_MISMATCH',
                                    'message': 'Token no corresponde al tenant del usuario',
                                    'expected_tenant': request.user.tenant_id,
                                    'token_tenant': tenant_id
                                }, status=403)
                    except Tenant.DoesNotExist:
                        return self._inactive_tenant_response()
        except (InvalidToken, TokenError, Tenant.DoesNotExist):
            # Si falla JWT, intentar desde usuario autenticado
            pass
        
        # Si no tenant desde JWT, fallback a usuario autenticado
        if not hasattr(request, 'tenant') or not request.tenant:
            if hasattr(request, 'user') and request.user.is_authenticated:
                # Recargar usuario con tenant para evitar lazy loading
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user = User.objects.select_related('tenant').get(pk=request.user.pk)
                    request.user = user
                except User.DoesNotExist:
                    logger.warning('Authenticated user not found while resolving tenant')
                    pass
                
                # Permitir acceso a super admins
                if self._is_superadmin(request.user):
                    request.tenant = None
                elif hasattr(request.user, 'tenant') and request.user.tenant:
                    # Validar que el tenant del usuario esté activo
                    user_tenant = request.user.tenant
                    
                    if user_tenant.deleted_at is not None or not user_tenant.is_active:
                        return self._inactive_tenant_response(user_tenant)
                    request.tenant = user_tenant
                else:
                    logger.warning('Authenticated user without tenant')
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
            # Verificar rutas que no requieren validación de suscripción
            subscription_exempt_paths = [
                '/api/subscriptions/renew/',
                '/api/tenants/subscription-status/',
                '/api/subscriptions/plans/',
            ]
            
            is_subscription_exempt = any(
                request.path.startswith(path) for path in subscription_exempt_paths
            )
            
            if not is_subscription_exempt:
                sync_subscription_state(request.tenant, save=True)
                access_level = request.tenant.get_access_level()
                
                if access_level == 'hidden':
                    return JsonResponse({
                        'error': 'Tenant archived',
                        'code': 'TENANT_ARCHIVED',
                        'message': 'This tenant is archived and unavailable.',
                    }, status=403)
                if access_level == 'blocked':
                    is_paid_expired = request.tenant.is_paid_access_expired() if hasattr(request.tenant, 'is_paid_access_expired') else False
                    if is_paid_expired:
                        return JsonResponse({
                            'error': 'Subscription expired',
                            'code': 'SUBSCRIPTION_EXPIRED',
                            'message': 'Your paid period has expired. Please renew to continue using the service.',
                            'renewal_url': '/client/payment',
                            'access_until': request.tenant.access_until.isoformat() if request.tenant.access_until else None
                        }, status=402)
                    return JsonResponse({
                        'error': 'Access blocked',
                        'code': 'SUBSCRIPTION_REQUIRED',
                        'message': 'Your trial has expired. Please subscribe to continue using the service.',
                        'upgrade_url': '/subscriptions/upgrade/'
                    }, status=402)
                elif access_level == 'limited':
                    request.grace_period = True
                    request.subscription_limited = True
            
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
