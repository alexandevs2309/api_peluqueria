from functools import wraps
from rest_framework.response import Response
from rest_framework import status

from apps.subscriptions_api.models import UserSubscription
from .permissions import RolePermission
from apps.roles_api.utils import log_admin_action

def role_required(*role_names):
    """
    Decorador que verifica que el usuario tenga al menos uno de los roles indicados.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            perm = RolePermission(allowed_roles=role_names)
            if not perm.has_permission(request, None):
                if not request.user or not request.user.is_authenticated:
                    return Response({"detail": "No autenticado."}, status=status.HTTP_401_UNAUTHORIZED)
                return Response({"detail": f"Se requiere uno de los roles: {', '.join(role_names)}."}, status=status.HTTP_403_FORBIDDEN)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def admin_action_log(action_name):
    """
    Decorador que registra la acción administrativa incluso si la vista lanza excepción.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            try:
                return view_func(request, *args, **kwargs)
            finally:
                if request.user and request.user.is_authenticated and request.user.is_active:
                    log_admin_action(request, action_name)
        return _wrapped_view
    return decorator

def permission_required(permission_class, *args, **kwargs):
    """
    Decorador flexible para aplicar cualquier clase de permiso con parámetros.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *a, **kw):
            perm = permission_class(*args, **kwargs)
            if not perm.has_permission(request, None):
                return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
            return view_func(request, *a, **kw)
        return _wrapped_view
    return decorator


def check_active_subscription(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return Response({"detail": "Autenticación requerida."}, status=status.HTTP_401_UNAUTHORIZED)

        has_active = UserSubscription.objects.filter(user=user, is_active=True).exists()
        if not has_active:
            return Response({"detail": "Se requiere una suscripción activa para acceder a este recurso."},
                            status=status.HTTP_403_FORBIDDEN)

        return view_func(request, *args, **kwargs)
    return _wrapped_view