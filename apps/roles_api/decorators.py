from functools import wraps
from django.http import JsonResponse
from .permission_checker import PermissionChecker
from .models import UserRole, AdminActionLog
from django.utils import timezone

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

def role_required(role_name):
    """Decorador simple para requerir un rol por nombre"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'No autenticado'}, status=401)

            tenant = getattr(request, 'tenant', None)

            has_role = UserRole.objects.filter(user=request.user, role__name=role_name)
            if tenant:
                has_role = has_role.filter(tenant=tenant)

            if not has_role.exists():
                return JsonResponse({'error': 'Sin permisos (rol requerido)'}, status=403)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_action_log(action_name):
    """Registra una acción administrativa simple en AdminActionLog"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)

            try:
                user = getattr(request, 'user', None)
                if user and user.is_authenticated:
                    # Obtener IP y UA de forma segura
                    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
                    ua = request.META.get('HTTP_USER_AGENT', '')
                    AdminActionLog.objects.create(user=user, action=action_name, ip_address=ip or '0.0.0.0', user_agent=ua or '', timestamp=timezone.now())
            except Exception:
                # No fallar la vista por problemas de logging
                pass

            return response
        return wrapper
    return decorator


def permission_required(permission_cls, **perm_kwargs):
    """Genera una instancia de permiso y verifica `has_permission` antes de ejecutar la vista."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'No autenticado'}, status=401)

            perm = permission_cls(**perm_kwargs) if perm_kwargs else permission_cls()
            try:
                allowed = perm.has_permission(request, None)
            except Exception:
                allowed = False

            if not allowed:
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