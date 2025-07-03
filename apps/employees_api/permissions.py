from rest_framework import permissions
from apps.auth_api.models import UserRole

class RolePermission(permissions.BasePermission):
    def __init__(self, allowed_roles=None):
        self.allowed_roles = allowed_roles or []

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        user_roles_names = UserRole.objects.filter(user=request.user).values_list('role__name', flat=True)
        return any(role in self.allowed_roles for role in user_roles_names)

def role_permission_for(roles):
    return type(
        f'RolePermissionFor{"_".join(roles)}',
        (RolePermission,),
        {
            '__init__': lambda self: RolePermission.__init__(self, allowed_roles=roles)
        }
    )

class IsAdminOrOwnStylist(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        user_roles_names = UserRole.objects.filter(user=request.user).values_list('role__name', flat=True)
        # Permitir solo a Admin para crear o modificar
        if hasattr(view, 'action') and view.action in ['create', 'update', 'partial_update', 'destroy']:
            return 'Admin' in user_roles_names
        # Para otras acciones permitir Admin o Stylist
        return any(role in ['Admin', 'Stylist'] for role in user_roles_names)

    def has_object_permission(self, request, view, obj):
        if UserRole.objects.filter(user=request.user, role__name='Admin').exists():
            return True
        return obj.user == request.user
