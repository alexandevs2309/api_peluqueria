# ============================================================
# FIX 4: apps/employees_api/earnings_views.py — permission_map
# PROBLEMA: Todos los métodos de nómina tienen permiso
#            'employees_api.view_employee_payroll' — incluyendo
#            register_payment, approve_period, recalculate_period.
#            Cualquier empleado con permiso VIEW puede pagar nóminas.
#            Además, _require_admin_role() es ad-hoc y no consistente
#            con el sistema RBAC.
#
# SOLUCIÓN: Separar permisos por operación. Mantener _require_admin_role
#            como segunda capa de defensa (defense-in-depth).
# ============================================================

# Reemplazar SOLO el bloque permission_map en PayrollViewSet:

class PayrollViewSet(viewsets.ViewSet):
    """ViewSet para gestión de nómina"""
    permission_classes = [TenantPermissionByAction]

    # ✅ CORREGIDO: Separar permisos de lectura vs. escritura sensible
    permission_map = {
        'list_periods':        'employees_api.view_employee_payroll',
        'get_receipt':         'employees_api.view_employee_payroll',

        # Operaciones que modifican estado financiero — requieren permiso específico
        'register_payment':    'employees_api.approve_payroll',
        'recalculate_period':  'employees_api.change_employee_payroll',
        'submit_for_approval': 'employees_api.change_employee_payroll',
        'approve_period':      'employees_api.approve_payroll',
        'reject_period':       'employees_api.approve_payroll',
    }

    # _require_admin_role se mantiene como segunda capa — defense in depth.
    # Si RBAC falla por misconfiguration, esta barrera sigue activa.
    def _require_admin_role(self, request):
        """Segunda capa: validar rol de admin (defense-in-depth)."""
        tenant = getattr(request, 'tenant', getattr(request.user, 'tenant', None))
        if get_effective_role_name(request.user, tenant=tenant) not in {'SuperAdmin', 'Client-Admin'}:
            raise PermissionDenied("No autorizado para operaciones de nómina.")

    # --- Resto del código sin cambios ---


# ============================================================
# FIX 4b: Migración para agregar permisos faltantes
# CREAR: apps/employees_api/migrations/XXXX_add_payroll_permissions.py
#
# Django no auto-genera permisos custom — hay que crearlos con
# una migración de datos (RunPython).
# ============================================================

from django.db import migrations


def add_payroll_permissions(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')

    # Obtener content type de Employee (o crear uno genérico para payroll)
    try:
        Employee = apps.get_model('employees_api', 'Employee')
        ct, _ = ContentType.objects.get_or_create(
            app_label='employees_api',
            model='employee',
        )
    except LookupError:
        return

    perms_to_create = [
        ('approve_payroll',          'Can approve payroll periods'),
        ('change_employee_payroll',  'Can recalculate and submit payroll periods'),
        ('view_employee_payroll',    'Can view payroll periods and receipts'),
    ]

    for codename, name in perms_to_create:
        Permission.objects.get_or_create(
            codename=codename,
            content_type=ct,
            defaults={'name': name},
        )


def remove_payroll_permissions(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    Permission.objects.filter(
        codename__in=[
            'approve_payroll',
            'change_employee_payroll',
            'view_employee_payroll',
        ],
        content_type__app_label='employees_api',
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        # Ajustar al último número de migración de employees_api
        ('employees_api', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(
            add_payroll_permissions,
            reverse_code=remove_payroll_permissions,
        ),
    ]
