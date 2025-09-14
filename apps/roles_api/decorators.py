from functools import wraps
from django.http import JsonResponse
from .permission_checker import PermissionChecker

def require_permission(permission_codename):
    """Decorador para verificar permisos en vistas"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'No autenticado'}, status=401)
                
            tenant = getattr(request, 'tenant', None)
            
            if not PermissionChecker.user_has_permission(
                request.user, permission_codename, tenant
            ):
                return JsonResponse({'error': 'Sin permisos'}, status=403)
                
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def require_module_access(module_name):
    """Decorador para verificar acceso a módulos"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'No autenticado'}, status=401)
                
            tenant = getattr(request, 'tenant', None)
            
            if not PermissionChecker.user_can_access_module(
                request.user, module_name, tenant
            ):
                return JsonResponse({'error': 'Sin acceso al módulo'}, status=403)
                
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator