"""
DRF Permission classes con filtrado por tenant
Usa UserRole + Role.permissions con aislamiento multi-tenant
"""
from rest_framework.permissions import BasePermission
from apps.roles_api.models import UserRole


def resolve_request_tenant(request):
    tenant = getattr(request, 'tenant', None)
    if tenant is not None:
        return tenant

    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False):
        return getattr(user, 'tenant', None)

    return None


class HasTenantPermission(BasePermission):
    """
    Verifica permisos basados en UserRole filtrado por request.tenant
    
    Uso:
        permission_classes = [HasTenantPermission('employees_api.view_employee')]
    """
    
    def __init__(self, required_permission=None):
        self.required_permission = required_permission
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # SuperAdmin siempre tiene acceso (ANTES de validar tenant)
        if request.user.is_superuser:
            return True
        
        # Usuarios normales requieren tenant
        tenant = resolve_request_tenant(request)
        if not tenant:
            return False
        
        # Si no se especificó permiso, solo validar autenticación + tenant
        if not self.required_permission:
            return True
        
        # Validar formato de permiso
        if '.' not in self.required_permission:
            return False
        
        app_label, codename = self.required_permission.split('.', 1)
        
        # Consultar UserRole filtrado por tenant
        user_roles = UserRole.objects.filter(
            user=request.user,
            tenant=tenant
        ).select_related('role').prefetch_related('role__permissions__content_type')
        
        # Verificar si algún rol tiene el permiso
        for user_role in user_roles:
            if user_role.role.permissions.filter(
                content_type__app_label=app_label,
                codename=codename
            ).exists():
                return True
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """
        Validación a nivel de objeto
        Por defecto usa has_permission, puede sobrescribirse
        """
        # Validar permiso base primero
        if not self.has_permission(request, view):
            return False
        
        # Validar que objeto pertenece al tenant
        tenant = resolve_request_tenant(request)
        if hasattr(obj, 'tenant'):
            return obj.tenant == tenant
        
        return True


def tenant_permission(perm):
    """
    Factory para crear permission classes dinámicamente
    
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
    Permisos por acción HTTP
    
    Uso en ViewSet:
        permission_classes = [TenantPermissionByAction]
        permission_map = {
            'list': 'employees_api.view_employee',
            'retrieve': 'employees_api.view_employee',
            'create': 'employees_api.add_employee',
            'update': 'employees_api.change_employee',
            'destroy': 'employees_api.delete_employee',
        }
    """
    
    # Permisos implícitos por nombre de rol (cuando no hay permisos asignados en BD)
    ROLE_IMPLICIT_PERMISSIONS = {
        'Client-Admin': '*',  # Acceso total al tenant
        # Manager mantiene operación diaria, pero no hereda poder de admin total.
        'Manager': [
            'view_appointment', 'add_appointment', 'change_appointment',
            'cancel_appointment', 'complete_appointment',
            'view_client', 'add_client', 'change_client',
            'view_employee',
            'view_service',
            'view_employee_reports', 'view_sales_reports', 'view_kpi_dashboard',
        ],
        'Client-Staff': [
            'view_employee', 'view_appointment', 'view_client',
            'view_service', 'view_sale', 'view_attendancerecord',
            'add_attendancerecord', 'change_attendancerecord',
        ],
        'Cajera': [
            'view_employee', 'view_appointment', 'add_appointment',
            'change_appointment', 'view_client', 'add_client',
            'change_client', 'view_service', 'view_sale', 'add_sale',
            'view_cashregister', 'add_cashregister', 'change_cashregister',
        ],
        'Estilista': [
            'view_employee', 'view_appointment', 'view_client',
            'view_service', 'view_sale', 'view_attendancerecord',
            'add_attendancerecord', 'change_attendancerecord',
        ],
        'Utility': ['view_employee', 'view_appointment', 'view_service'],
    }

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # SuperAdmin siempre tiene acceso (ANTES de validar tenant)
        if request.user.is_superuser:
            return True
        
        # Usuarios normales requieren tenant
        tenant = resolve_request_tenant(request)
        if not tenant:
            return False
        
        # Obtener permiso requerido según acción
        permission_map = getattr(view, 'permission_map', {})
        action = getattr(view, 'action', None)
        
        if not action or action not in permission_map:
            return False
        
        required_perm = permission_map[action]
        
        if '.' not in required_perm:
            return False
        
        app_label, codename = required_perm.split('.', 1)
        
        user_roles = UserRole.objects.filter(
            user=request.user,
            tenant=tenant
        ).select_related('role').prefetch_related('role__permissions__content_type')
        
        for user_role in user_roles:
            role = user_role.role

            # 1. Verificar permisos explícitos en BD
            if role.permissions.filter(
                content_type__app_label=app_label,
                codename=codename
            ).exists():
                return True

            # 2. Fallback: permisos implícitos por nombre de rol
            implicit = self.ROLE_IMPLICIT_PERMISSIONS.get(role.name)
            if implicit == '*' or (isinstance(implicit, list) and codename in implicit):
                return True
        
        return False
