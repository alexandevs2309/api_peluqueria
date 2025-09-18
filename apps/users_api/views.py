from django.forms import ValidationError
from django.shortcuts import render
from django.db import models
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from apps.auth_api.models import AccessLog

from rest_framework import viewsets, permissions
from django.contrib.auth import get_user_model
from apps.users_api.serializers import AccessLogSerializer, UserSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.employees_api.permissions import RolePermission

User = get_user_model()

class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.roles.filter(name='Super-Admin').exists()
        )

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(is_deleted=False).order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]  # Temporal para debugging

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'full_name']
    filterset_fields = ['is_active', 'roles']

    def get_permissions(self):
        if self.action == 'available_for_employee':
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

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

    @action(detail=False, methods=["get"], url_path="available-for-employee")
    def available_for_employee(self, request):
        """Usuarios disponibles para ser asignados como empleados"""
        from apps.employees_api.models import Employee
        
        # Usuarios que no son empleados aún
        existing_employee_users = Employee.objects.values_list('user_id', flat=True)
        available_users = User.objects.filter(
            is_active=True,
            is_deleted=False
        ).exclude(id__in=existing_employee_users)
        
        # Si no es SuperAdmin, filtrar por tenant
        if not request.user.roles.filter(name='Super-Admin').exists():
            if hasattr(request.user, 'tenant') and request.user.tenant:
                # Solo usuarios del mismo tenant o sin tenant
                available_users = available_users.filter(
                    models.Q(tenant=request.user.tenant) | models.Q(tenant__isnull=True)
                )
            else:
                available_users = available_users.none()
        
        serializer = UserSerializer(available_users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="deleted")
    def deleted_users(self, request):
        """Listar usuarios eliminados"""
        deleted_users = User.objects.filter(is_deleted=True).order_by('-date_joined')
        serializer = UserSerializer(deleted_users, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        """Restaurar usuario eliminado"""
        try:
            user = User.objects.get(pk=pk, is_deleted=True)
            user.is_deleted = False
            user.save()
            return Response({"detail": f"Usuario {user.email} restaurado correctamente."})
        except User.DoesNotExist:
            return Response({"error": "Usuario no encontrado o no está eliminado."}, status=404)
