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


# Relaciones habituales de los modelos hijos que no guardan `tenant_id` propio.
# La resolución es recursiva y acotada para no seguir relaciones circulares.
_OBJECT_TENANT_PATHS = (
    'tenant',
    'employee',
    'user',
    'client',
    'stylist',
    'created_by',
    'barbershop',
    'service',
    'appointment',
    'sale',
    'payment',
    'invoice',
    'subscription',
    'ticket',
    'recipient',
    'role_target',
)


def resolve_object_tenant(view, obj, _seen=None, _root=True):
    """Resuelve el tenant de un objeto, incluso si es un modelo hijo.

    Un ViewSet puede declarar ``get_object_tenant(obj)`` para relaciones propias.
    Si no se puede resolver, devuelve ``None`` y el permiso se deniega salvo
    declaración explícita de catálogo global.
    """
    if _root:
        custom_resolver = getattr(view, 'get_object_tenant', None)
        if callable(custom_resolver):
            custom_tenant = custom_resolver(obj)
            if custom_tenant is not None:
                return custom_tenant

    if _seen is None:
        _seen = set()
    marker = (type(obj).__name__, id(obj))
    if marker in _seen:
        return None
    _seen.add(marker)

    for attr in _OBJECT_TENANT_PATHS:
        try:
            related = getattr(obj, attr)
        except (AttributeError, TypeError):
            continue
        if related is None:
            continue
        if attr == 'tenant':
            return related
        nested = resolve_object_tenant(view, related, _seen, _root=False)
        if nested is not None:
            return nested
    return None


def _same_tenant(object_tenant, request_tenant):
    """Compara tenant por id para aceptar tanto instancias como ids."""
    if object_tenant is None or request_tenant is None:
        return False
    return getattr(object_tenant, 'id', object_tenant) == getattr(
        request_tenant, 'id', request_tenant
    )


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
        object_tenant = resolve_object_tenant(view, obj)
        if object_tenant is not None:
            return _same_tenant(object_tenant, tenant)

        # Solo los views que declaran explícitamente trabajar con objetos globales
        # pueden omitir el chequeo de tenant.
        return bool(getattr(view, 'allow_tenantless_objects', False))


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

        if request.user.is_superuser:
            return True

        tenant = resolve_request_tenant(request)
        object_tenant = resolve_object_tenant(view, obj)
        if object_tenant is not None:
            return _same_tenant(object_tenant, tenant)

        # Deny-by-default: un objeto sin tenant no hereda permisos por arte de magia.
        # Los catálogos globales legítimos lo declaran explícitamente en la vista.
        return bool(getattr(view, 'allow_tenantless_objects', False))
