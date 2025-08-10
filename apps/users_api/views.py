<<<<<<< HEAD
from django.forms import ValidationError
from django.shortcuts import render
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from apps.auth_api.models import AccessLog
=======
from django.shortcuts import render
>>>>>>> origin/master


from rest_framework import viewsets, permissions
from django.contrib.auth import get_user_model
<<<<<<< HEAD
from apps.users_api.serializers import AccessLogSerializer, UserSerializer

from rest_framework.decorators import action
from rest_framework.response import Response
=======
from apps.users_api.serializers import UserSerializer
>>>>>>> origin/master

User = get_user_model()

class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
<<<<<<< HEAD
        print("Usuario autenticado:", request.user.email)
        print("Roles:", request.user.roles.all())
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.roles.filter(name='Super-Admin').exists()
        )


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(is_deleted=False).order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'full_name']
    filterset_fields = ['is_active', 'roles']

    def create(self, request, *args, **kwargs):
        print("[DEBUG] Datos recibidos:", request.data)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        print("[DEBUG] Datos recibidos para actualizar:", request.data)
        return super().update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        if instance.roles.filter(name='Super-Admin').exists() and User.objects.count() <= 1:
            raise ValidationError("No puedes eliminar el único Super-Admin.")
        instance.is_deleted = True
        instance.save()


    

    @action(detail=True, methods=["post"])
    def change_password(self, request, pk=None):
        user = self.get_object()
        new_password = request.data.get("password")
        if not new_password:
            return Response({"error": "Se requiere una nueva contraseña."}, status=400)
        
        user.set_password(new_password)
        user.save()
        return Response({"detail": "Contraseña actualizada correctamente."})



    @action(detail=False, methods=["get"])
    def export(self, request):
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="usuarios.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Email', 'Nombre completo', 'Estado', 'Roles'])

        for user in self.get_queryset():
            roles = ', '.join([r.name for r in user.roles.all()])
            writer.writerow([user.id, user.email, user.full_name, 'Activo' if user.is_active else 'Inactivo', roles])

        return response

    @action(detail=True, methods=["get"])
    def logs(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
            logs = AccessLog.objects.filter(user=user).order_by('-timestamp')
            page = self.paginate_queryset(logs)
            serializer = AccessLogSerializer(page, many=True) if page is not None else AccessLogSerializer(logs, many=True)
            return self.get_paginated_response(serializer.data) if page else Response(serializer.data)
        except User.DoesNotExist:
            return Response({"error": "Usuario no encontrado."}, status=404)
=======
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
>>>>>>> origin/master
