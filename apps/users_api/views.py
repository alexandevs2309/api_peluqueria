from django.shortcuts import render


from rest_framework import viewsets, permissions
from django.contrib.auth import get_user_model
from apps.users_api.serializers import UserSerializer

User = get_user_model()

class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Verificar si el usuario tiene el rol Super-Admin
        # Puede ser directamente en user.role o en user.roles
        if hasattr(request.user, 'role'):
            return request.user.role == 'Super-Admin'
        
        # Si roles es una lista de objetos
        if hasattr(request.user, 'roles'):
            roles = request.user.roles
            if isinstance(roles, list):
                return any(role.get('name') == 'Super-Admin' for role in roles)
            elif hasattr(roles, 'all'):  # QuerySet
                return roles.filter(name='Super-Admin').exists()
        
        return False

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
