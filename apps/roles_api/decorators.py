from functools import wraps
from rest_framework.response import Response
from rest_framework import status
# No necesitas importar get_user_model o UserRole aquí si accedes vía request.user.assigned_users
# from django.contrib.auth import get_user_model
# from .models import UserRole

def role_required(*role_names):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return Response({"detail": "No autenticado."}, status=status.HTTP_401_UNAUTHORIZED)

            user_roles_queryset = request.user.roles.all() 

            # Opción A (Recomendada - coherente con el M2M en User):
            user_roles_names = user_roles_queryset.values_list('name', flat=True)

        

            if not user_roles_names.exists(): # Revisa si el QuerySet está vacío
                return Response({"detail": "No tienes roles asignados."}, status=status.HTTP_403_FORBIDDEN)

            if not any(role_name in role_names for role_name in user_roles_names):
                return Response({"detail": f"Se requiere uno de los roles: {', '.join(role_names)}."}, status=status.HTTP_403_FORBIDDEN)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator