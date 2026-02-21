from rest_framework.permissions import BasePermission


class IsClientAdmin(BasePermission):
    """Permission para CLIENT_ADMIN solamente"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'Client-Admin'
        )
