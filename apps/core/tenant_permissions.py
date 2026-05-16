"""
DRF permission classes con filtrado por tenant.

Usa UserRole + Role.permissions con aislamiento multi-tenant.
La autorizacion es deny-by-default y solo acepta permisos explicitos en BD.
"""
import logging

from rest_framework.permissions import BasePermission

from apps.roles_api.models import UserRole

logger = logging.getLogger(__name__)


def resolve_request_tenant(request):
    """Obtener tenant del request: primero del middleware, luego del user."""
    tenant = getattr(request, 'tenant', None)
    if tenant is not None:
        return tenant

    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False):
        return getattr(user, 'tenant', None)

    return None


def _check_permission_in_db(user, tenant, app_label, codename):
    """Verificar permisos explicitos via UserRole -> Role -> Permission."""
    user_roles = UserRole.objects.filter(
        user=user,
        tenant=tenant
    ).select_related('role').prefetch_related('role__permissions__content_type')

    for user_role in user_roles:
        if user_role.role.permissions.filter(
            content_type__app_label=app_label,
            codename=codename
        ).exists():
            return True

    role_names = list(user_roles.values_list('role__name', flat=True))
    logger.warning(
        "Permiso denegado user=%s tenant=%s perm=%s.%s roles=%s",
        user.id, tenant.id, app_label, codename, role_names,
    )
    return False


class HasTenantPermission(BasePermission):
    """
    Permiso basado en un codename especifico.

    Uso:
        permission_classes = [tenant_permission('employees_api.view_employee')]
    """
    required_permission = None

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        tenant = resolve_request_tenant(request)
        if not tenant:
            return False

        if not self.required_permission:
            return True

        if '.' not in self.required_permission:
            return False

        app_label, codename = self.required_permission.split('.', 1)
        return _check_permission_in_db(request.user, tenant, app_label, codename)

    def has_object_permission(self, request, view, obj):
        if not self.has_permission(request, view):
            return False

        tenant = resolve_request_tenant(request)
        if hasattr(obj, 'tenant'):
            return obj.tenant == tenant

        return True


def tenant_permission(perm):
    """
    Factory para crear permission classes dinamicamente.

    Uso:
        permission_classes = [tenant_permission('employees_api.add_employee')]
    """
    return type(
        f'HasTenantPermission_{perm.replace(".", "_")}',
        (HasTenantPermission,),
        {'required_permission': perm}
    )


class TenantPermissionByAction(BasePermission):
    """
    Permisos por accion DRF ViewSet o por metodo HTTP APIView.

    Si action/metodo no esta en permission_map, se deniega por defecto.
    No existe fallback implicito por nombre de rol.
    """

    def _resolve_action(self, request, view):
        action = getattr(view, 'action', None)
        if action:
            return action

        return request.method.upper() if request.method else None

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        tenant = resolve_request_tenant(request)
        if not tenant:
            return False

        permission_map = getattr(view, 'permission_map', {})
        action = self._resolve_action(request, view)

        if not action or action not in permission_map:
            return False

        required_perm = permission_map[action]

        if '.' not in required_perm:
            return False

        app_label, codename = required_perm.split('.', 1)
        return _check_permission_in_db(request.user, tenant, app_label, codename)

    def has_object_permission(self, request, view, obj):
        if not self.has_permission(request, view):
            return False

        tenant = resolve_request_tenant(request)
        if hasattr(obj, 'tenant'):
            return obj.tenant == tenant
        if hasattr(obj, 'user') and hasattr(obj.user, 'tenant'):
            return obj.user.tenant == tenant

        return True
