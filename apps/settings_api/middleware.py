from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from .models import SystemSettings


class MaintenanceModeMiddleware(MiddlewareMixin):
    """Middleware para manejar el modo mantenimiento"""

    def process_request(self, request):
        # Permitir acceso a admin, health checks y landing
        if (request.path == '/admin' or request.path.startswith('/admin/') or 
            request.path.startswith('/api/healthz/') or
            request.path.startswith('/api/system-settings/') or
            request.path.startswith('/api/settings/public-branding/') or
            request.path.startswith('/landing') or
            request.path.startswith('/pages/landing') or
            request.path.startswith('/api/auth/register') or
            request.path.startswith('/api/auth/login') or
            request.path.startswith('/api/auth/cookie-login') or
            request.path.startswith('/api/auth/cookie-refresh') or
            request.path.startswith('/api/auth/verify')):
            return None

        try:
            settings = SystemSettings.get_settings()
            if settings.maintenance_mode:
                # Autenticar desde JWT cookies para detectar superadmins
                if not (hasattr(request, 'user') and request.user.is_authenticated):
                    try:
                        from apps.auth_api.authentication import CookieJWTAuthentication
                        auth_result = CookieJWTAuthentication().authenticate(request)
                        if auth_result:
                            request.user, _ = auth_result
                    except Exception:
                        pass

                # Permitir acceso solo a superusuarios
                if not (getattr(request, 'user', None) and request.user.is_authenticated and request.user.is_superuser):
                    return JsonResponse({
                        'error': 'Sistema en modo mantenimiento',
                        'message': 'El sistema está temporalmente fuera de servicio. Inténtelo más tarde.'
                    }, status=503)
        except Exception:
            pass

        return None
