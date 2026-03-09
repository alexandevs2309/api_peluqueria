from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from datetime import datetime
from apps.subscriptions_api.models import UserSubscription
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class SubscriptionValidationMiddleware(MiddlewareMixin):
    """
    Middleware para validar estado de suscripción y expiración de planes
    """
    
    def process_request(self, request):
        # Excluir rutas que no requieren validación
        exempt_paths = [
            '/api/auth/',
            '/api/schema/',
            '/api/docs/',
            '/api/healthz/',
            '/admin/',
            '/api/subscriptions/plans/',  # Permitir ver planes
            '/api/subscriptions/register/',  # Permitir registro
            '/api/subscriptions/register-with-plan/',  # Permitir registro con plan
            '/api/subscriptions/renew/',  # Permitir renovación
            '/api/payments/',
            '/api/billing/',
            '/api/settings/contact/',
        ]
        
        for exempt_path in exempt_paths:
            if request.path.startswith(exempt_path):
                return None
        
        # Solo aplicar a usuarios autenticados
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
            
        # SuperAdmin siempre tiene acceso
        if request.user.is_superuser or request.user.role == 'SuperAdmin' or request.user.roles.filter(name='Super-Admin').exists():
            return None
            
        # Validar tenant y plan
        if not hasattr(request.user, 'tenant') or not request.user.tenant:
            return JsonResponse({
                'error': 'No tenant assigned',
                'code': 'NO_TENANT',
                'action_required': 'contact_admin'
            }, status=403)
            
        tenant = request.user.tenant
        
        # Validar si tenant está activo
        if not tenant.is_active:
            return JsonResponse({
                'error': 'Tenant suspended',
                'code': 'TENANT_SUSPENDED',
                'action_required': 'contact_admin'
            }, status=403)
            
        # Validar expiración de plan FREE con período de gracia
        if (tenant.subscription_status == 'trial' and 
            tenant.trial_end_date and 
            tenant.trial_end_date < timezone.now().date()):
            
            # Calcular días desde expiración
            days_expired = (timezone.now().date() - tenant.trial_end_date).days
            
            # Período de gracia de 3 días
            if days_expired <= 3:
                # Permitir acceso limitado durante período de gracia
                request.grace_period = True
                request.days_remaining = 3 - days_expired
                return None
            else:
                return JsonResponse({
                    'error': 'Free trial expired',
                    'code': 'TRIAL_EXPIRED',
                    'expired_date': tenant.trial_end_date.isoformat(),
                    'days_expired': days_expired,
                    'action_required': 'upgrade_plan',
                    'upgrade_url': '/subscriptions/plans/'
                }, status=402)  # Payment Required

        # Validar expiración de acceso pago (fecha de corte)
        if (
            tenant.subscription_status == 'active' and
            tenant.access_until and
            tenant.access_until < timezone.now()
        ):
            return JsonResponse({
                'error': 'Subscription expired',
                'code': 'SUBSCRIPTION_EXPIRED',
                'expired_date': tenant.access_until.isoformat(),
                'action_required': 'renew_subscription',
                'renewal_url': '/client/payment'
            }, status=402)
            
        # Validar suscripciones de usuario expiradas
        user_subscription = UserSubscription.objects.filter(
            user=request.user, 
            is_active=True
        ).first()
        
        if user_subscription and user_subscription.end_date < timezone.now():
            # Marcar como expirada
            user_subscription.is_active = False
            user_subscription.save()
            
            return JsonResponse({
                'error': 'Subscription expired',
                'code': 'SUBSCRIPTION_EXPIRED',
                'expired_date': user_subscription.end_date.isoformat(),
                'action_required': 'renew_subscription',
                'renewal_url': '/client/payment'
            }, status=402)
        
        # Validar plan activo
        if not tenant.subscription_plan:
            return JsonResponse({
                'error': 'No subscription plan',
                'code': 'NO_PLAN',
                'action_required': 'select_plan'
            }, status=402)
            
        return None


class APIRateLimitMiddleware(MiddlewareMixin):
    """
    Middleware para rate limiting diferenciado por plan de suscripción.
    Diseño:
    - Límites separados para lectura y escritura.
    - Exclusión de endpoints de polling/estado frecuentes.
    - Contadores por hora, por usuario y por scope.
    """
    
    # Límites por plan (requests por hora)
    RATE_LIMITS = {
        'basic': {'read': 1200, 'write': 250},
        'standard': {'read': 5000, 'write': 1000},
        'premium': {'read': 15000, 'write': 3000},
        'enterprise': None,  # Ilimitado
    }

    # Endpoints públicos (sin throttling de este middleware)
    EXEMPT_PREFIXES = [
        '/api/auth/',
        '/api/healthz/',
        '/api/schema/',
        '/api/docs/',
    ]

    # Endpoints de alta frecuencia de lectura que no deben penalizar UX.
    EXEMPT_READ_PREFIXES = [
        '/api/notifications/',
        '/api/subscriptions/me/entitlements/',
        '/api/subscriptions/renew/',
        '/api/settings/barbershop/',
    ]
    
    def process_request(self, request):
        # Solo aplicar a rutas /api/
        if not request.path.startswith('/api/'):
            return None
        
        # Excluir rutas públicas
        for exempt_path in self.EXEMPT_PREFIXES:
            if request.path.startswith(exempt_path):
                return None
        
        # Solo aplicar a usuarios autenticados
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        # SuperAdmin sin límite
        if request.user.is_superuser:
            return None
        
        # Obtener plan del usuario
        tenant = getattr(request.user, 'tenant', None)
        if not tenant:
            return None
        
        subscription_plan = getattr(tenant, 'subscription_plan', None)
        if not subscription_plan:
            return None
        
        plan_name = subscription_plan.name
        plan_limits = self.RATE_LIMITS.get(plan_name)
        
        # Plan enterprise sin límite
        if plan_limits is None:
            return None

        is_read = request.method in ('GET', 'HEAD', 'OPTIONS')
        if is_read:
            for prefix in self.EXEMPT_READ_PREFIXES:
                if request.path.startswith(prefix):
                    return None

        scope = 'read' if is_read else 'write'
        rate_limit = plan_limits.get(scope)
        if rate_limit is None:
            return None

        # Clave de cache por usuario/scope y por hora para evitar crecimiento infinito
        current_hour_bucket = timezone.now().strftime('%Y%m%d%H')
        cache_key = f'api_rate_limit:{request.user.id}:{scope}:{current_hour_bucket}'

        # Obtener contador actual (fail-open controlado si Redis/cache falla)
        try:
            current_count = cache.get(cache_key, 0)
        except Exception as exc:
            logger.error("RateLimit cache get failed: %s", str(exc))
            return None

        # Verificar límite
        if current_count >= rate_limit:
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'code': 'RATE_LIMIT_EXCEEDED',
                'limit': rate_limit,
                'period': '1 hour',
                'plan': plan_name,
                'scope': scope,
                'action_required': 'upgrade_plan' if plan_name != 'enterprise' else 'wait'
            }, status=429)
        
        # Incrementar contador (expira en 1 hora)
        try:
            cache.set(cache_key, current_count + 1, 3600)
        except Exception as exc:
            logger.error("RateLimit cache set failed: %s", str(exc))
            return None
        
        # Agregar headers de rate limit
        request.rate_limit_remaining = rate_limit - current_count - 1
        request.rate_limit_limit = rate_limit
        request.rate_limit_scope = scope
        
        return None
    
    def process_response(self, request, response):
        # Agregar headers de rate limit a la respuesta
        if hasattr(request, 'rate_limit_remaining'):
            response['X-RateLimit-Limit'] = str(request.rate_limit_limit)
            response['X-RateLimit-Remaining'] = str(request.rate_limit_remaining)
            response['X-RateLimit-Reset'] = str(3600)  # 1 hora en segundos
            response['X-RateLimit-Scope'] = str(getattr(request, 'rate_limit_scope', 'read'))
        
        return response
