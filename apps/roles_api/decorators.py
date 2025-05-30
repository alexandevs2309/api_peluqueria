from functools import wraps
from rest_framework.response import Response
from rest_framework import status

def role_required(*role_names):
    """
    Decorador para verificar si el usuario tiene uno de los roles requeridos."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return Response({"detail": "No autenticado."}, status=status.HTTP_401_UNAUTHORIZED)

            user_roles = getattr(request.user, 'roles', None)
            if not user_roles.exists():
                return Response({"detail": "No tienes roles asignados."}, status=status.HTTP_403_FORBIDDEN)

            if not user_roles.filter(name__in=role_names).exists():
                return Response({"detail": f"Se requiere uno de los roles: {', '.join(role_names)}."}, status=status.HTTP_403_FORBIDDEN)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
