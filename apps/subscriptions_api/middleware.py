from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from datetime import datetime
from apps.subscriptions_api.models import UserSubscription
from django.core.cache import cache
import logging
import threading
import time
from apps.tenants_api.subscription_lifecycle import sync_subscription_state

logger = logging.getLogger(__name__)

# Contador de emergencia, por proceso, usado solo cuando el backend de caché falla.
# Evita que una caída de Redis convierta el límite por plan en un límite inexistente.
_EMERGENCY_RATE_LIMIT_LOCK = threading.Lock()
_EMERGENCY_RATE_LIMIT_COUNTERS = {}
_EMERGENCY_RATE_LIMIT_TTL = 3600

BILLING_WEBHOOK_PATHS = [
    '/api/billing/webhooks/stripe/',
    '/api/payments/stripe/webhook/',
]

# Se conserva por compatibilidad de importaciones. Estas rutas siguen exentas del
# paywall, pero desde el endurecimiento consumen el límite por plan.
BILLING_ACCESS_PATHS = [
    '/api/payments/payments/create_subscription_payment/',
    '/api/subscriptions/renew/',
]

PAYWALL_SAFE_PREFIXES = [
    '/api/subscriptions/me/entitlements/',
    '/api/subscriptions/renew/',
    '/api/tenants/current/',
    '/api/tenants/locale/',
    '/api/tenants/subscription-status/',
]

PAYWALL_SAFE_READONLY_PREFIXES = [
    '/api/notifications/',
]

# Escrituras que permiten regularizar la cuenta: no deben quedar bloqueadas por
# el paywall (renovación, webhooks de cobro y cierre de sesión).
PAYWALL_RECOVERY_PREFIXES = tuple(dict.fromkeys(
    PAYWALL_SAFE_PREFIXES
    + BILLING_ACCESS_PATHS
    + BILLING_WEBHOOK_PATHS
    + ['/api/auth/cookie-logout/', '/api/auth/cookie-refresh/']
))


def is_limited_business_write(request) -> bool:
    """Escritura de negocio sujeta al bloqueo por suscripción limitada."""
    if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
        return False
    return not any(request.path.startswith(prefix) for prefix in PAYWALL_RECOVERY_PREFIXES)


def payment_required_response(status_value: str, tenant=None):
    """Respuesta 402 homogénea para past_due y suspended."""
    return JsonResponse({
        'error': 'Subscription past due' if status_value == 'past_due' else 'Subscription expired',
        'code': 'PAYMENT_REQUIRED',
        'message': (
            'Su cuenta tiene facturas pendientes de pago. Por favor complete el pago '
            'para restablecer las operaciones de escritura.'
            if status_value == 'past_due' else
            'Su suscripción está suspendida. Por favor renueve para restablecer las operaciones de escritura.'
        ),
        'renewal_url': '/client/payment',
        'subscription_status': status_value,
        'tenant_id': getattr(tenant, 'id', None),
    }, status=402)


class SubscriptionValidationMiddleware(MiddlewareMixin):
    """
    Middleware para validar estado de suscripción y expiración de planes
    """
    
    def process_request(self, request):
        if any(request.path.startswith(prefix) for prefix in PAYWALL_SAFE_PREFIXES):
            return None

        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            for prefix in PAYWALL_SAFE_READONLY_PREFIXES:
                if request.path.startswith(prefix):
                    return None

        for exempt_path in BILLING_WEBHOOK_PATHS + BILLING_ACCESS_PATHS:
            if request.path.startswith(exempt_path):
                return None

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
            '/api/settings/contact/',
            '/api/booking/',  # Auto-agendamiento público
        ]
        
        for exempt_path in exempt_paths:
            if request.path.startswith(exempt_path):
                return None
        
        # Solo aplicar a usuarios autenticados
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
            
        # SuperAdmin siempre tiene acceso; is_superuser es la fuente de verdad.
        if getattr(request.user, 'is_superuser', False):
            return None
            
        # Validar tenant y plan
        if not hasattr(request.user, 'tenant') or not request.user.tenant:
            return JsonResponse({
                'error': 'No tenant assigned',
                'code': 'NO_TENANT',
                'action_required': 'contact_admin'
            }, status=403)
            
        tenant = getattr(request, 'tenant', request.user.tenant)

        # Cache sync: solo sincronizar cada 5 minutos para evitar query + save en cada request.
        # cache.add es atómico en Redis y LocMem: evita que varias peticiones concurrentes
        # ejecuten la sincronización y se pisen mutuamente.
        _sync_cache_key = f'sub_sync:{tenant.id}'
        try:
            _should_sync = cache.add(_sync_cache_key, True, 300)
        except Exception as exc:
            logger.warning("Subscription sync cache unavailable, syncing inline: %s", exc)
            _should_sync = True
        if _should_sync:
            sync_subscription_state(tenant, save=True)
        
        if tenant.subscription_status in {'archived', 'cancelled'}:
            return JsonResponse({
                'error': 'Tenant archived',
                'code': 'TENANT_ARCHIVED',
                'action_required': 'contact_support'
            }, status=403)

        # BE-04: consumir el estado limitado antes de cualquier escritura de negocio.
        # TenantMiddleware ya marca el flag en el grace period; aquí se fuerza también
        # para past_due/suspended aunque el flag no haya llegado a setearse.
        limited_status = tenant.subscription_status
        if limited_status not in {'past_due', 'suspended'} and getattr(request, 'subscription_limited', False):
            limited_status = getattr(request, 'subscription_status', None) or 'past_due'
        if limited_status in {'past_due', 'suspended'} and is_limited_business_write(request):
            request.subscription_limited = True
            request.subscription_status = limited_status
            return payment_required_response(limited_status, tenant)

        # Validar si tenant está activo
        if not tenant.is_active and tenant.subscription_status not in {'past_due'}:
            return JsonResponse({
                'error': 'Tenant suspended',
                'code': 'TENANT_SUSPENDED',
                'action_required': 'contact_admin'
            }, status=403)
            
        # Validar expiración de trial — el grace period lo maneja TenantMiddleware
        if (tenant.subscription_status == 'trial' and
            tenant.trial_end_date and
            tenant.trial_end_date < timezone.now().date()):
            days_expired = (timezone.now().date() - tenant.trial_end_date).days
            if days_expired > 3:
                return JsonResponse({
                    'error': 'Trial expired',
                    'code': 'TRIAL_EXPIRED',
                    'expired_date': tenant.trial_end_date.isoformat(),
                    'days_expired': days_expired,
                    'action_required': 'upgrade_plan',
                    'upgrade_url': '/subscriptions/plans/'
                }, status=402)
            # Dentro del grace period: TenantMiddleware ya seteó request.grace_period
            return None

        if tenant.subscription_status == 'past_due':
            request.subscription_limited = True
            request.subscription_status = 'past_due'
            return None

        # Validar expiración de acceso pago / estados bloqueados
        if tenant.subscription_status == 'suspended':
            return JsonResponse({
                'error': 'Subscription expired',
                'code': 'SUBSCRIPTION_SUSPENDED',
                'expired_date': tenant.access_until.isoformat() if tenant.access_until else None,
                'action_required': 'renew_subscription',
                'renewal_url': '/client/payment'
            }, status=402)
            
        # Validar suscripciones de usuario expiradas (con cache 5 min).
        # La clave incluye el tenant para no mezclar entitlements de un mismo user.id
        # entre negocios distintos.
        _usub_cache_key = f'usub:{tenant.id}:{request.user.id}'
        user_subscription = cache.get(_usub_cache_key)
        if user_subscription is None:
            user_subscription = UserSubscription.objects.filter(
                user=request.user,
                is_active=True
            ).first()
            cache.set(_usub_cache_key, user_subscription or False, 300)
        
        if user_subscription is False:
            user_subscription = None

        if user_subscription:
            # Si está cancelada (cancelled_at set) pero end_date no ha pasado, aún tiene acceso
            if user_subscription.cancelled_at and user_subscription.end_date and user_subscription.end_date > timezone.now():
                request.subscription_cancelled = True
                request.subscription_access_until = user_subscription.end_date
                return None

            if user_subscription.end_date and user_subscription.end_date < timezone.now():
                user_subscription.is_active = False
                user_subscription.save()
                cache.delete(_usub_cache_key)
                
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

    El contador es atómico (`cache.add` + `cache.incr`). Si el backend de caché
    falla, se usa un contador local por proceso con el mismo límite (degradación
    controlada, fail-closed): nunca se permite tráfico ilimitado por indisponibilidad
    de Redis.
    """

    # Límites por plan (requests por hora). No se modifican los valores comerciales.
    # 'pro' conserva los límites de Premium según el mapeo legacy aprobado R1.
    BASIC_RATE_LIMITS = {'read': 10000, 'write': 500}
    PREMIUM_RATE_LIMITS = {'read': 150000, 'write': 30000}
    RATE_LIMITS = {
        'basic': BASIC_RATE_LIMITS,
        'standard': {'read': 50000, 'write': 5000},
        'premium': PREMIUM_RATE_LIMITS,
        'pro': PREMIUM_RATE_LIMITS,
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
        '/api/tenants/locale/',
        '/api/tenants/current/',
        '/api/auth/verify/',
    ]

    @staticmethod
    def _emergency_increment(cache_key, rate_limit):
        """Contador local thread-safe usado únicamente si falla el caché."""
        now = time.monotonic()
        cutoff = now - _EMERGENCY_RATE_LIMIT_TTL
        with _EMERGENCY_RATE_LIMIT_LOCK:
            expired = [key for key, (_, updated_at) in _EMERGENCY_RATE_LIMIT_COUNTERS.items()
                       if updated_at < cutoff]
            for key in expired:
                _EMERGENCY_RATE_LIMIT_COUNTERS.pop(key, None)

            count, _ = _EMERGENCY_RATE_LIMIT_COUNTERS.get(cache_key, (0, now))
            count += 1
            # El límite local nunca puede exceder el límite del plan: así el contador
            # queda saturado y las peticiones posteriores son rechazadas.
            _EMERGENCY_RATE_LIMIT_COUNTERS[cache_key] = (min(count, rate_limit + 1), now)
            return _EMERGENCY_RATE_LIMIT_COUNTERS[cache_key][0]

    def process_request(self, request):
        # Solo aplicar a rutas /api/
        if not request.path.startswith('/api/'):
            return None

        for exempt_path in self.EXEMPT_PREFIXES:
            if request.path.startswith(exempt_path):
                return None

        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None

        # Las rutas de cobro siguen exentas del paywall (PAYWALL_SAFE_PREFIXES),
        # pero consumen cuota del plan: un plan básico no puede crear sesiones de
        # pago externas sin límite.
        user = request.user
        tenant = getattr(request, 'tenant', None) or getattr(user, 'tenant', None)
        # La única excepción es el flag is_superuser (fuente de verdad según AGENTS.md).
        # No confiar en un nombre de rol legado evita bypasses por payload.
        if getattr(user, 'is_superuser', False):
            return None

        if not tenant:
            return None

        subscription_plan = getattr(tenant, 'subscription_plan', None)
        # BE-02: un tenant sin plan NO queda sin límite; cae al plan básico.
        plan_name = str(getattr(subscription_plan, 'name', '') or '').strip().lower()
        if plan_name == 'enterprise':
            return None

        plan_limits = self.RATE_LIMITS.get(plan_name, self.BASIC_RATE_LIMITS)
        if plan_limits is None:  # defensivo: enterprise ya se resolvió arriba
            plan_limits = self.BASIC_RATE_LIMITS
        if plan_name not in self.RATE_LIMITS:
            logger.warning(
                "Unknown subscription plan %r for tenant=%s; applying basic rate limit",
                plan_name, tenant.id,
            )

        is_read = request.method in ('GET', 'HEAD', 'OPTIONS')
        if is_read:
            for prefix in self.EXEMPT_READ_PREFIXES:
                if request.path.startswith(prefix):
                    return None

        scope = 'read' if is_read else 'write'
        rate_limit = plan_limits.get(scope)
        if rate_limit is None:
            return None

        # Clave por tenant + usuario + scope + hora. El tenant lo fija el backend,
        # nunca el payload del cliente.
        current_hour_bucket = timezone.now().strftime('%Y%m%d%H')
        cache_key = f'api_rate_limit:{tenant.id}:{user.id}:{scope}:{current_hour_bucket}'

        degraded = False
        try:
            cache.add(cache_key, 0, 3600)
            current_count = cache.incr(cache_key, 1)
        except Exception as exc:
            degraded = True
            logger.warning("RateLimit cache unavailable, using local limiter: %s", exc)
            current_count = self._emergency_increment(cache_key, rate_limit)

        request.rate_limit_remaining = max(0, rate_limit - current_count)
        request.rate_limit_limit = rate_limit
        request.rate_limit_scope = scope
        request.rate_limit_degraded = degraded

        if current_count > rate_limit:
            logger.warning(
                "RATE_LIMIT_EXCEEDED user=%s tenant=%s path=%s plan=%s scope=%s count=%d limit=%d degraded=%s",
                user.id, tenant.id, request.path, plan_name, scope,
                current_count, rate_limit, degraded,
            )
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'code': 'RATE_LIMIT_EXCEEDED',
                'limit': rate_limit,
                'period': '1 hour',
                'plan': plan_name,
                'scope': scope,
                'action_required': 'upgrade_plan' if plan_name != 'enterprise' else 'wait'
            }, status=429)

        return None

    def process_response(self, request, response):
        # Agregar headers de rate limit a la respuesta
        if hasattr(request, 'rate_limit_remaining'):
            response['X-RateLimit-Limit'] = str(request.rate_limit_limit)
            response['X-RateLimit-Remaining'] = str(request.rate_limit_remaining)
            response['X-RateLimit-Reset'] = str(3600)  # 1 hora en segundos
            response['X-RateLimit-Scope'] = str(getattr(request, 'rate_limit_scope', 'read'))
            if getattr(request, 'rate_limit_degraded', False):
                response['X-RateLimit-Degraded'] = '1'

        return response
