from rest_framework import viewsets, permissions, decorators, response, status, serializers
from django.contrib.auth import get_user_model
from apps.auth_api.permissions import IsSuperAdmin
from .models import Tenant
from .serializers import TenantSerializer
from django.contrib.contenttypes.models import ContentType
from apps.audit_api.models import AuditLog
from apps.settings_api.utils import validate_tenant_limit
User = get_user_model()

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
    pagination_class = None
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def get_permissions(self):
        # Permitir acceso autenticado para subscription_status
        if self.action == 'subscription_status':
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        # ✅ ESTANDARIZADO: Usar is_superuser en lugar de roles
        if self.request.user.is_superuser:
            return Tenant.objects.filter(deleted_at__isnull=True)
        # Otros usuarios no tienen acceso
        return Tenant.objects.none()

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
        if not validate_tenant_limit():
            raise serializers.ValidationError({
                'error': 'Límite de clientes alcanzado',
                'message': 'No se pueden crear más clientes. Contacte al administrador.'
            })
        tenant = serializer.save(owner=self.request.user)

        AuditLog.objects.create(
            user=self.request.user,
            action='CREATE',
            description=f"Creó un nuevo tenant: {tenant.name}",
            content_type=ContentType.objects.get_for_model(tenant),
            object_id=tenant.id,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            source='SYSTEM',
            extra_data={
                'tenant_name': tenant.name,
                'owner_id': tenant.owner.id if tenant.owner else None
            }
    )
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete de tenant"""
        tenant = self.get_object()
        tenant.soft_delete()
        
        AuditLog.objects.create(
            user=request.user,
            action='DELETE',
            description=f"Eliminó tenant: {tenant.name}",
            content_type=ContentType.objects.get_for_model(tenant),
            object_id=tenant.id,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            source='SYSTEM'
        )
        
        return response.Response(status=status.HTTP_204_NO_CONTENT)

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
    
    @decorators.action(detail=False, methods=["get"])
    def current(self, request):
        """Get current user's tenant"""
        if request.user.tenant:
            serializer = self.get_serializer(request.user.tenant)
            return response.Response(serializer.data)
        return response.Response({"error": "No tenant assigned"}, status=404)
    
    @decorators.action(detail=False, methods=["get"])
    def subscription_status(self, request):
        """Check subscription status - will trigger middleware validation"""
        if request.user.tenant:
            return response.Response({"status": "active"})
        return response.Response({"error": "No tenant assigned"}, status=403)
    
    @decorators.action(detail=False, methods=["post"])
    def bulk_activate(self, request):
        """Bulk activate tenants"""
        tenant_ids = request.data.get('tenant_ids', [])
        tenants = Tenant.objects.filter(id__in=tenant_ids)
        tenants.update(is_active=True)
        return response.Response({"activated": len(tenants)})
    
    @decorators.action(detail=False, methods=["post"])
    def bulk_deactivate(self, request):
        """Bulk deactivate tenants"""
        tenant_ids = request.data.get('tenant_ids', [])
        tenants = Tenant.objects.filter(id__in=tenant_ids)
        tenants.update(is_active=False)
        return response.Response({"deactivated": len(tenants)})
    
    @decorators.action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        """Bulk soft delete tenants"""
        tenant_ids = request.data.get('tenant_ids', [])
        
        if not tenant_ids:
            return response.Response(
                {"error": "No tenant IDs provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(tenant_ids) > 20:
            return response.Response(
                {"error": "Maximum 20 tenants per operation"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tenants = Tenant.objects.filter(id__in=tenant_ids)
        deleted_count = 0
        
        for tenant in tenants:
            tenant.soft_delete()
            
            AuditLog.objects.create(
                user=request.user,
                action='BULK_DELETE',
                description=f"Eliminó tenant en bulk: {tenant.name}",
                content_type=ContentType.objects.get_for_model(tenant),
                object_id=tenant.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                source='SYSTEM',
                extra_data={
                    'tenant_id': tenant.id,
                    'tenant_name': tenant.name
                }
            )
            deleted_count += 1
        
        return response.Response({"deleted": deleted_count})
