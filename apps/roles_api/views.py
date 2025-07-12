from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .permissions import role_permission_for
from .models import Role
from .serializers import PermissionSerializer, RoleSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import Permission
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, extend_schema_view
from .utils import log_admin_action

@extend_schema_view(
    list=extend_schema(description="Lista todos los roles disponibles."),
    retrieve=extend_schema(description="Obtiene los detalles de un rol específico."),
    create=extend_schema(description="Crea un nuevo rol."),
    update=extend_schema(description="Actualiza un rol existente."),
    partial_update=extend_schema(description="Actualiza parcialmente un rol."),
    destroy=extend_schema(description="Elimina un rol."),
)
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all().order_by('id')
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, role_permission_for(['Admin'])]

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'permissions__codename']
    pagination_class = PageNumberPagination
    ordering_fields = ['id', 'name']
    search_fields = ['name']
    ordering = ['id']

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        log_admin_action(request, 'List roles')
        return response

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        log_admin_action(request, 'Retrieve role')
        return response

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        log_admin_action(request, 'Create role')
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        log_admin_action(request, 'Update role')
        return response

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        log_admin_action(request, 'Delete role')
        return response

    @extend_schema(
        responses={200: PermissionSerializer(many=True)},
        description="Lista todos los permisos disponibles."
    )
    @action(detail=False, methods=["get"], url_path="permissions")
    def list_permissions(self, request):
        perms = Permission.objects.all()
        page = self.paginate_queryset(perms)
        if page is not None:
            serializer = PermissionSerializer(page, many=True)
            log_admin_action(request, 'List permissions')
            return self.get_paginated_response(serializer.data)
        serializer = PermissionSerializer(perms, many=True)
        log_admin_action(request, 'List permissions')
        return Response(serializer.data)