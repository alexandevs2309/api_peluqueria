from django.http import JsonResponse
from .permission_config import PERMISSION_CAPABILITIES

class PermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Verificar permisos antes de procesar la vista
        if request.user.is_authenticated:
            path = request.path
            method = request.method
            
            # Buscar si la ruta requiere permisos específicos
            required_permission = self.get_required_permission(path, method)
            
            if required_permission and not request.user.has_perm(required_permission):
                return JsonResponse({'error': 'Sin permisos'}, status=403)
        
        response = self.get_response(request)
        return response
    
    def get_required_permission(self, path, method):
        """Determina qué permiso se necesita para una ruta"""
        for perm_code, config in PERMISSION_CAPABILITIES.items():
            endpoints = config.get('endpoints', [])
            methods = config.get('methods', [])
            
            for endpoint in endpoints:
                # Comparar ruta (simplificado)
                if endpoint.replace('{id}', '') in path and method in methods:
                    return f'app_name.{perm_code}'
        
        return None