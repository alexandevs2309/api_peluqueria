from rest_framework.permissions import BasePermission
from .models import UserRole

class RolePermission(BasePermission):
    """ Permite acceso si el usuario tiene alguno de los roles permitidos. """
    allowed_roles = ['Admin']  # Configurado explícitamente

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Opción 1: Usar UserRole (modelo intermedio)
        user_roles = UserRole.objects.filter(user=request.user).values_list('role__name', flat=True)
        
        # Opción 2: Usar la relación directa many-to-many
        # user_roles = request.user.roles.values_list('name', flat=True)
        
        return any(role in self.allowed_roles for role in user_roles)