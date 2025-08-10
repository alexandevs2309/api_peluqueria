from rest_framework.permissions import BasePermission

class IsOwnerOrAdmin(BasePermission):
    """
    Permite acceso si el usuario es el dueño del recurso o un superusuario.
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_superuser
