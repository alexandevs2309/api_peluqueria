from rest_framework import viewsets, permissions, decorators, response, status
from django.contrib.auth import get_user_model
from .models import Tenant
from .serializers import TenantSerializer
from django.contrib.contenttypes.models import ContentType
from apps.audit_api.models import AuditLog
User = get_user_model()

class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.roles.filter(name='Super-Admin').exists()
        )

class TenantViewSet(viewsets.ModelViewSet):
    """
    ViewSet para manejar tenants:
    - Activar/desactivar
    - Obtener estadísticas
    - Registrar auditoría
    """
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = None  # Disable pagination for tenants list

    def get_permissions(self):
        if self.action in ['activate', 'deactivate']:
            return [permissions.IsAdminUser()]
        return [permission() for permission in self.permission_classes]

    def _create_audit_log(self, user, action, target):
        AuditLog.objects.create(
            user=user,
            action=action,
            description=f"{action} tenant: {target.name}",
            content_type=ContentType.objects.get_for_model(target),
            object_id=target.id,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            source='SYSTEM'
        )

    def perform_create(self, serializer):
        tenant = serializer.save(owner=self.request.user)

        AuditLog.objects.create(
            user=self.request.user,
            action='CREATE',
            description=f"Creó un nuevo tenant: {tenant.name}",
            content_type=ContentType.objects.get_for_model(tenant),
            object_id=tenant.id,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            source='SYSTEM',  # O 'USERS' si lo prefieres
            extra_data={
                'tenant_name': tenant.name,
                'owner_id': tenant.owner.id if tenant.owner else None
            }
    )

    @decorators.action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        tenant = self.get_object()
        if tenant.is_active:
            return response.Response(
                {"status": "tenant already active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        tenant.is_active = True
        tenant.save()
        self._create_audit_log(request.user, "Activated tenant", tenant)
        serializer = self.get_serializer(tenant)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        tenant = self.get_object()
        if not tenant.is_active:
            return response.Response(
                {"status": "tenant already inactive"},
                status=status.HTTP_400_BAD_REQUEST
            )
        tenant.is_active = False
        tenant.save()
        self._create_audit_log(request.user, "Deactivated tenant", tenant)
        serializer = self.get_serializer(tenant)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        tenant = self.get_object()
        current_users = User.objects.filter(tenant=tenant).count()
        # current_employees = Employee.objects.filter(tenant=tenant).count()  # si tienes Employee

        return response.Response({
            "max_users": tenant.max_users,
            "max_employees": tenant.max_employees,
            "current_users": current_users,
            # "current_employees": current_employees,
        }, status=status.HTTP_200_OK)
