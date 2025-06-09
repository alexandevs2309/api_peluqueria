from rest_framework.permissions import BasePermission
from .models import UserRole

class RolePermission(BasePermission):
    """
    Verifica si el usuario tiene uno de los roles permitidos.
    """
    def __init__(self, allowed_roles=None):
        self.allowed_roles = allowed_roles or []

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        user_roles_names = UserRole.objects.filter(user=request.user).values_list('role__name', flat=True)
        return any(role in self.allowed_roles for role in user_roles_names)

# ✅ Esta función crea una clase de permiso personalizada con los roles que tú quieras
def role_permission_for(roles):
    return type(
        f'RolePermissionFor{"_".join(roles)}',
        (RolePermission,),
        {
            '__init__': lambda self: RolePermission.__init__(self, allowed_roles=roles)
        }
    )
