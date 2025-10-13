from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from .models import SystemSettings


class MaintenanceModeMiddleware(MiddlewareMixin):
    """Middleware para manejar el modo mantenimiento"""
    
    def process_request(self, request):
        # Permitir acceso a admin, health checks y landing
        if (request.path.startswith('/admin/') or 
            request.path.startswith('/api/healthz/') or
            request.path.startswith('/api/system-settings/') or
            request.path.startswith('/landing') or
            request.path.startswith('/pages/landing') or
            request.path.startswith('/api/auth/register')):
            return None
            
        try:
            settings = SystemSettings.get_settings()
            if settings.maintenance_mode:
                # Permitir acceso solo a superusuarios
                if not (hasattr(request, 'user') and request.user.is_authenticated and request.user.is_superuser):
                    return JsonResponse({
                        'error': 'Sistema en modo mantenimiento',
                        'message': 'El sistema está temporalmente fuera de servicio. Inténtelo más tarde.'
                    }, status=503)
        except Exception:
            # Si hay error al obtener configuraciones, continuar normalmente
            pass
            
        return None