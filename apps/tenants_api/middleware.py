from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from .models import Tenant

class TenantMiddleware(MiddlewareMixin):
    """
    Middleware para manejar multitenancy basado en el usuario autenticado
    """
    
    def process_request(self, request):
        # Solo aplicar a rutas de API que no sean admin
        if not request.path.startswith('/api/') or request.path.startswith('/api/admin/'):
            return None
            
        # Rutas que no requieren tenant
        exempt_paths = [
            '/api/auth/',
            '/api/schema/',
            '/api/docs/',
            '/api/healthz/',
            '/api/system-settings/',
        ]
        
        for exempt_path in exempt_paths:
            if request.path.startswith(exempt_path):
                return None
        
        # Si el usuario está autenticado, asignar su tenant
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Super-Admin puede acceder a todo
            if request.user.roles.filter(name='Super-Admin').exists():
                request.tenant = None  # Sin restricción de tenant
                return None
                
            # Usuarios normales deben tener tenant
            if hasattr(request.user, 'tenant') and request.user.tenant:
                request.tenant = request.user.tenant
                return None
            else:
                # Usuario sin tenant - solo para rutas específicas
                if request.path.startswith('/api/subscriptions/me/'):
                    request.tenant = None
                    return None
                    
                return JsonResponse({
                    'error': 'Usuario sin tenant asignado',
                    'code': 'NO_TENANT'
                }, status=403)
        
        # Usuario no autenticado
        request.tenant = None
        return None