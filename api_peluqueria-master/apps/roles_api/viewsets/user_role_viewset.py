import logging

from rest_framework import viewsets, serializers, status
from rest_framework.response import Response

from apps.core.tenant_permissions import TenantPermissionByAction
from apps.roles_api.models import Role, UserRole
from apps.roles_api.serializers import UserRoleSerializer

logger = logging.getLogger(__name__)


class UserRoleViewSet(viewsets.ModelViewSet):
    serializer_class = UserRoleSerializer
    permission_classes = [TenantPermissionByAction]
    pagination_class = None

    permission_map = {
        'list':           'roles_api.view_userrole',
        'retrieve':       'roles_api.view_userrole',
        'create':         'roles_api.add_userrole',
        'update':         'roles_api.change_userrole',
        'partial_update': 'roles_api.change_userrole',
        'destroy':        'roles_api.delete_userrole',
    }

    def _resolve_tenant(self):
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return tenant
        user = getattr(self.request, 'user', None)
        if user and hasattr(user, 'tenant'):
            return user.tenant
        return None

    def get_queryset(self):
        tenant = self._resolve_tenant()
        if not tenant:
            return UserRole.objects.none()
        return UserRole.objects.filter(
            tenant=tenant
        ).select_related('user', 'role', 'tenant')

    def perform_create(self, serializer):
        tenant = self._resolve_tenant()
        role = serializer.validated_data.get('role')

        if role and self._is_restricted_role(role):
            raise serializers.ValidationError(
                {'role': 'No tiene permiso para asignar este rol'}
            )

        user = serializer.validated_data.get('user')
        if user and not self._user_belongs_to_tenant(user, tenant):
            raise serializers.ValidationError(
                {'user': 'El usuario no pertenece a este tenant'}
            )

        serializer.save(tenant=tenant)

    def perform_update(self, serializer):
        if 'role' in serializer.validated_data:
            role = serializer.validated_data['role']
            if self._is_restricted_role(role):
                raise serializers.ValidationError(
                    {'role': 'No tiene permiso para asignar este rol'}
                )

        tenant = self._resolve_tenant()
        user = serializer.validated_data.get('user')
        if user and not self._user_belongs_to_tenant(user, tenant):
            raise serializers.ValidationError(
                {'user': 'El usuario no pertenece a este tenant'}
            )

        serializer.save()

    def _is_restricted_role(self, role):
        if role.scope == 'GLOBAL':
            return True
        if role.name in ('owner', 'Super-Admin', 'SuperAdmin', 'internal_support'):
            return True
        return False

    def _user_belongs_to_tenant(self, user, tenant):
        if not tenant:
            return False
        return UserRole.objects.filter(
            user=user, tenant=tenant
        ).exists() or getattr(user, 'tenant_id', None) == tenant.id
