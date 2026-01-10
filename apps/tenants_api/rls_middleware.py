"""
RLS-based Tenant Middleware
Reemplaza apps/tenants_api/middleware.py
"""
from django.db import connection
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from apps.tenants_api.models import Tenant
import logging

logger = logging.getLogger(__name__)

class RLSTenantMiddleware(MiddlewareMixin):
    """
    Middleware que establece tenant_id en PostgreSQL session
    para Row Level Security automático
    """
    
    def process_request(self, request):
        # Reset tenant context
        self._set_tenant_context(0)
        
        # Skip para SuperAdmin y rutas públicas
        if self._should_skip_tenant_check(request):
            return None
            
        # Obtener tenant del usuario autenticado
        tenant_id = self._get_tenant_from_request(request)
        
        if not tenant_id:
            return JsonResponse({
                'error': 'Tenant required',
                'code': 'TENANT_REQUIRED'
            }, status=403)
        
        # Verificar tenant activo
        if not self._is_tenant_active(tenant_id):
            return JsonResponse({
                'error': 'Tenant suspended or inactive',
                'code': 'TENANT_INACTIVE'
            }, status=403)
        
        # Establecer contexto RLS
        self._set_tenant_context(tenant_id)
        request.tenant_id = tenant_id
        
        return None
    
    def process_response(self, request, response):
        # Limpiar contexto al final del request
        self._set_tenant_context(0)
        return response
    
    def _set_tenant_context(self, tenant_id):
        """Establece tenant_id en sesión PostgreSQL"""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.current_tenant_id', %s, false)",
                [str(tenant_id)]
            )
    
    def _should_skip_tenant_check(self, request):
        """Rutas que no requieren tenant"""
        skip_paths = [
            '/admin/',
            '/api/auth/login/',
            '/api/auth/register/',
            '/api/health/',
            '/api/schema/',
        ]
        return any(request.path.startswith(path) for path in skip_paths)
    
    def _get_tenant_from_request(self, request):
        """Extrae tenant_id del usuario autenticado"""
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        # SuperAdmin puede acceder a cualquier tenant
        if request.user.role == 'SuperAdmin':
            # Permitir override por header para SuperAdmin
            return request.META.get('HTTP_X_TENANT_ID', 0)
        
        return getattr(request.user, 'tenant_id', None)
    
    def _is_tenant_active(self, tenant_id):
        """Verifica si tenant está activo"""
        if tenant_id == 0:  # SuperAdmin context
            return True
            
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            return tenant.is_active and tenant.subscription_status in ['active', 'trial']
        except Tenant.DoesNotExist:
            return False