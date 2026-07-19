# ============================================================
# FIX 7: apps/core/tenant_permissions.py — Eliminar bypass implícito
# PROBLEMA: ROLE_IMPLICIT_PERMISSIONS en TenantPermissionByAction
#            asigna permisos por nombre de rol textual. Cualquier
#            persona que cree un rol llamado "Client-Admin" en
#            cualquier tenant hereda permiso '*' (acceso total)
#            sin necesitar assignments en BD.
#
# SOLUCIÓN: Eliminar el fallback implícito. Todos los permisos
#            deben estar asignados explícitamente en BD.
#            Para migración segura: script que auto-asigna permisos
#            a roles existentes con esos nombres.
# ============================================================

# ---- Cambio en tenant_permissions.py ----
# En TenantPermissionByAction.has_permission(), ELIMINAR el bloque:
#
#   # 2. Fallback: permisos implícitos por nombre de rol
#   implicit = self.ROLE_IMPLICIT_PERMISSIONS.get(role.name)
#   if implicit == '*' or (isinstance(implicit, list) and codename in implicit):
#       return True
#
# Y ELIMINAR la clase variable ROLE_IMPLICIT_PERMISSIONS completa.
#
# El método has_permission() queda así:

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        tenant = resolve_request_tenant(request)
        if not tenant:
            return False

        permission_map = getattr(view, 'permission_map', {})
        action = getattr(view, 'action', None)

        # Para APIView class-based (GET, POST, etc.) — compatibilidad
        if not action:
            action = request.method.upper()

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
            # Solo permisos explícitos en BD — sin fallback por nombre
            if role.permissions.filter(
                content_type__app_label=app_label,
                codename=codename
            ).exists():
                return True

        return False


# ============================================================
# FIX 7b: Script de migración — asignar permisos explícitos a roles
# EJECUTAR ANTES de desplegar el cambio anterior.
# Archivo: scripts/assign_default_role_permissions.py
# Uso: python manage.py shell < scripts/assign_default_role_permissions.py
# ============================================================

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.roles_api.models import Role

# Mapa de permisos por nombre de rol
# Igual al ROLE_IMPLICIT_PERMISSIONS que se va a eliminar
ROLE_PERMISSIONS = {
    'Client-Admin': '__all__',  # Se maneja por separado abajo
    'Manager': [
        ('appointments_api', 'view_appointment'),
        ('appointments_api', 'add_appointment'),
        ('appointments_api', 'change_appointment'),
        ('appointments_api', 'cancel_appointment'),
        ('appointments_api', 'complete_appointment'),
        ('clients_api',      'view_client'),
        ('clients_api',      'add_client'),
        ('clients_api',      'change_client'),
        ('employees_api',    'view_employee'),
        ('services_api',     'view_service'),
        ('reports_api',      'view_employee_reports'),
        ('reports_api',      'view_sales_reports'),
        ('reports_api',      'view_kpi_dashboard'),
    ],
    'Client-Staff': [
        ('employees_api',    'view_employee'),
        ('appointments_api', 'view_appointment'),
        ('clients_api',      'view_client'),
        ('services_api',     'view_service'),
        ('pos_api',          'view_sale'),
        ('employees_api',    'view_attendancerecord'),
        ('employees_api',    'add_attendancerecord'),
        ('employees_api',    'change_attendancerecord'),
    ],
    'Cajera': [
        ('employees_api',    'view_employee'),
        ('appointments_api', 'view_appointment'),
        ('appointments_api', 'add_appointment'),
        ('appointments_api', 'change_appointment'),
        ('clients_api',      'view_client'),
        ('clients_api',      'add_client'),
        ('clients_api',      'change_client'),
        ('services_api',     'view_service'),
        ('pos_api',          'view_sale'),
        ('pos_api',          'add_sale'),
        ('pos_api',          'view_cashregister'),
        ('pos_api',          'add_cashregister'),
        ('pos_api',          'change_cashregister'),
        ('inventory_api',    'view_product'),
    ],
    'Estilista': [
        ('employees_api',    'view_employee'),
        ('appointments_api', 'view_appointment'),
        ('clients_api',      'view_client'),
        ('services_api',     'view_service'),
        ('pos_api',          'view_sale'),
        ('employees_api',    'view_attendancerecord'),
        ('employees_api',    'add_attendancerecord'),
        ('employees_api',    'change_attendancerecord'),
    ],
    'Utility': [
        ('employees_api',    'view_employee'),
        ('appointments_api', 'view_appointment'),
        ('services_api',     'view_service'),
    ],
}

assigned_total = 0
skipped = []

for role_name, perms in ROLE_PERMISSIONS.items():
    roles = Role.objects.filter(name=role_name)
    if not roles.exists():
        print(f"⚠️  Rol '{role_name}' no encontrado — omitir")
        continue

    for role in roles:
        if perms == '__all__':
            # Client-Admin: asignar todos los permisos de las apps del SaaS
            target_apps = [
                'appointments_api', 'clients_api', 'employees_api',
                'services_api', 'inventory_api', 'pos_api', 'billing_api',
                'reports_api', 'settings_api', 'notifications_api', 'audit_api',
            ]
            all_perms = Permission.objects.filter(
                content_type__app_label__in=target_apps
            )
            role.permissions.set(all_perms)
            print(f"✅ {role_name} (id={role.id}): {all_perms.count()} permisos asignados")
            assigned_total += all_perms.count()
        else:
            for app_label, codename in perms:
                try:
                    ct = ContentType.objects.get(app_label=app_label)
                    perm = Permission.objects.get(content_type=ct, codename=codename)
                    role.permissions.add(perm)
                    assigned_total += 1
                except (ContentType.DoesNotExist, Permission.DoesNotExist):
                    skipped.append(f"{app_label}.{codename}")

            print(f"✅ {role_name} (id={role.id}, tenant={getattr(role, 'tenant_id', 'global')}): permisos asignados")

print(f"\n✅ Total asignados: {assigned_total}")
if skipped:
    print(f"⚠️  Permisos no encontrados (crear con migración): {set(skipped)}")
