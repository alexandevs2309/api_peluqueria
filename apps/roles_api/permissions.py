from rest_framework.permissions import BasePermission

class RolePermission(BasePermission):
    """ Permite acceso si el usuario tiene alguno de los roles permitidos. """
    allowed_roles = ['admin'] # Configurado explicitamente

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        user_roles = getattr(request.user, 'roles', None)
        if not user_roles.exists():
            return False

        return user_roles.filter(name__in=self.allowed_roles).exists()
