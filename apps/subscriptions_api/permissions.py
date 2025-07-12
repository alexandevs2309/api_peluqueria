from rest_framework.permissions import BasePermission

class IsSuperuserOrReadOnly(BasePermission):

    def has_permission(self, request, view):
        # Allow read-only access for all users
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        # Allow full access for superusers
        return request.user and request.user.is_superuser