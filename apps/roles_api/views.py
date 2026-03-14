from rest_framework import viewsets,filters
from rest_framework.permissions import IsAuthenticated
from apps.core.permissions import IsSuperAdmin
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

CANONICAL_ROLES = [
    {'name': 'Super-Admin', 'scope': 'GLOBAL', 'description': 'Administrador del SaaS'},
    {'name': 'Soporte', 'scope': 'GLOBAL', 'description': 'Equipo de soporte tecnico'},
    {'name': 'Client-Admin', 'scope': 'TENANT', 'description': 'Administrador de peluqueria'},
    {'name': 'Client-Staff', 'scope': 'TENANT', 'description': 'Empleado general'},
    {'name': 'Estilista', 'scope': 'TENANT', 'description': 'Estilista/Peluquero'},
    {'name': 'Cajera', 'scope': 'TENANT', 'description': 'Cajera/Recepcionista'},
    {'name': 'Manager', 'scope': 'TENANT', 'description': 'Encargado operativo'},
    {'name': 'Utility', 'scope': 'TENANT', 'description': 'Personal de apoyo'},
]


def ensure_canonical_roles() -> None:
    for role_data in CANONICAL_ROLES:
        role, created = Role.objects.get_or_create(
            name=role_data['name'],
            defaults={
                'scope': role_data['scope'],
                'description': role_data['description']
            }
        )
        if not created:
            changed = False
            if role.scope != role_data['scope']:
                role.scope = role_data['scope']
                changed = True
            if not role.description:
                role.description = role_data['description']
                changed = True
            if changed:
                role.save(update_fields=['scope', 'description'])

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
    permission_classes = [IsSuperAdmin]  # Solo SuperAdmin puede gestionar roles

    filter_backends = [DjangoFilterBackend , DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'permissions__codename','scope', 'module']
    pagination_class = None  # Desactivar paginación
    ordering_fields = ['id', 'name' , 'module']
    search_fields = ['name', 'description','module']
    ordering = ['id']

    def get_queryset(self):
        ensure_canonical_roles()
        return super().get_queryset()

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
        perms = Permission.objects.all().order_by('content_type__app_label', 'codename')
        serializer = PermissionSerializer(perms, many=True)
        log_admin_action(request, 'List permissions')
        return Response({'results': serializer.data})
