from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from datetime import datetime

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
            '/api/subscriptions/plans/',
            '/api/subscriptions/register/',
            '/api/settings/contact/',
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
            
        # Validar expiración de plan FREE
        if (tenant.subscription_status == 'trial' and 
            tenant.trial_end_date and 
            tenant.trial_end_date < timezone.now().date()):
            
            return JsonResponse({
                'error': 'Free trial expired',
                'code': 'TRIAL_EXPIRED',
                'expired_date': tenant.trial_end_date.isoformat(),
                'action_required': 'upgrade_plan',
                'upgrade_url': '/api/subscriptions/plans/'
            }, status=402)  # Payment Required
            
        # Validar plan activo
        if not tenant.subscription_plan:
            return JsonResponse({
                'error': 'No subscription plan',
                'code': 'NO_PLAN',
                'action_required': 'select_plan'
            }, status=402)
            
        return None