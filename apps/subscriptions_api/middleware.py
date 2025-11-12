from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from datetime import datetime
from apps.subscriptions_api.models import UserSubscription

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
            '/api/subscriptions/',
            '/api/payments/',
            '/api/billing/',
            '/api/settings/contact/',
            '/api/pos/',  # Permitir operaciones POS
        ]
        
        for exempt_path in exempt_paths:
            if request.path.startswith(exempt_path):
                return None
        
        # Solo aplicar a usuarios autenticados
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
            
        # SuperAdmin siempre tiene acceso
        if request.user.is_superuser or request.user.roles.filter(name='Super-Admin').exists():
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