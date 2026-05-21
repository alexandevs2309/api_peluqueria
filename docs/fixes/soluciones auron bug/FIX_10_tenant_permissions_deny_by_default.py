"""
============================================================
FIX 10: apps/core/tenant_permissions.py — CRÍTICO
PROBLEMA: La tabla VULNERABILITIES_TABLE.csv documenta que la clase
          TenantPermissionByAction tiene un fallback inseguro:
          "permite GET para acciones no mapeadas" → línea marcada
          como CRÍTICA. Además el ROLE_IMPLICIT_PERMISSIONS permite
          bypass total por nombre de rol sin BD.

SOLUCIÓN:
  1. Deny-by-default: si action no está en permission_map → False
  2. Soporte para APIView (HTTP method como action)
  3. Eliminar ROLE_IMPLICIT_PERMISSIONS — reemplazar por permisos
     explícitos en BD (ejecutar FIX_7 script primero)
  4. Mantener has_object_permission con tenant check

INSTRUCCIÓN: Reemplazar apps/core/tenant_permissions.py completo.
============================================================
"""
from rest_framework.permissions import BasePermission
from apps.roles_api.models import UserRole


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
    """
    Verificar si el usuario tiene el permiso via UserRole → Role → Permission.
    Solo permisos explícitos en BD — sin fallback implícito.
    """
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
    return False


class HasTenantPermission(BasePermission):
    """
    Permiso basado en un codename específico.
    Uso: permission_classes = [tenant_permission('employees_api.view_employee')]
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
            return True  # Solo autenticación + tenant requerido

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
    Factory para crear permission classes dinámicamente.
    Uso: permission_classes = [tenant_permission('employees_api.add_employee')]
    """
    return type(
        f'HasTenantPermission_{perm.replace(".", "_")}',
        (HasTenantPermission,),
        {'required_permission': perm}
    )


class TenantPermissionByAction(BasePermission):
    """
    Permisos por acción DRF (ViewSet) o por método HTTP (APIView).

    ViewSet:
        permission_classes = [TenantPermissionByAction]
        permission_map = {
            'list':   'employees_api.view_employee',
            'create': 'employees_api.add_employee',
        }

    APIView (class-based):
        permission_classes = [TenantPermissionByAction]
        permission_map = {
            'GET':  'reports_api.view_kpi_dashboard',
            'POST': 'reports_api.add_report',
        }

    ✅ DENY-BY-DEFAULT: Si action/method no está en permission_map → False.
    ✅ SIN FALLBACK IMPLÍCITO por nombre de rol.
    """

    def _resolve_action(self, request, view):
        """
        Obtener la 'action' para buscar en permission_map.
        ViewSets tienen view.action ('list', 'create', 'my_action').
        APIViews usan el método HTTP ('GET', 'POST', 'PATCH', 'DELETE').
        """
        # DRF ViewSet
        action = getattr(view, 'action', None)
        if action:
            return action

        # APIView class-based
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

        # ✅ CRÍTICO: Deny-by-default si action no está mapeada
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
