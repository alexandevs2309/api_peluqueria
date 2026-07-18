"""
Script para configurar roles y permisos del sistema RBAC
Ejecutar: python manage.py shell < scripts/setup_roles_permissions.py
"""
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.roles_api.models import Role
from apps.employees_api.models import Employee
from apps.pos_api.models import Sale, CashRegister, Promotion
from apps.clients_api.models import Client
from apps.inventory_api.models import Product
from apps.services_api.models import Service
from apps.appointments_api.models import Appointment
from apps.reports_api.models import ReportPermission

print("🔧 Configurando roles y permisos...")

# Crear roles base
roles_config = {
    'Client-Admin': {
        'scope': 'TENANT',
        'description': 'Administrador del tenant - acceso total',
        'permissions': 'all'
    },
    'Manager': {
        'scope': 'TENANT',
        'description': 'Manager - lectura total, escritura limitada',
        'permissions': 'read_all_write_limited'
    },
    'Cajera': {
        'scope': 'TENANT',
        'description': 'Cajera - solo POS y ventas',
        'permissions': 'pos_only'
    },
    'Estilista': {
        'scope': 'TENANT',
        'description': 'Estilista - ver citas y clientes',
        'permissions': 'stylist'
    }
}

for role_name, config in roles_config.items():
    role, created = Role.objects.get_or_create(
        name=role_name,
        defaults={
            'scope': config['scope'],
            'description': config['description']
        }
    )
    if created:
        print(f"✅ Rol creado: {role_name}")
    else:
        print(f"ℹ️  Rol existente: {role_name}")

# Obtener content types
employee_ct = ContentType.objects.get_for_model(Employee)
sale_ct = ContentType.objects.get_for_model(Sale)
cashregister_ct = ContentType.objects.get_for_model(CashRegister)
promotion_ct = ContentType.objects.get_for_model(Promotion)
client_ct = ContentType.objects.get_for_model(Client)
product_ct = ContentType.objects.get_for_model(Product)
service_ct = ContentType.objects.get_for_model(Service)
appointment_ct = ContentType.objects.get_for_model(Appointment)
report_permission_ct = ContentType.objects.get_for_model(ReportPermission, for_concrete_model=False)

# Asignar permisos a Client-Admin (todos)
client_admin = Role.objects.get(name='Client-Admin')
admin_perms = Permission.objects.filter(
    content_type__in=[employee_ct, sale_ct, client_ct, appointment_ct, cashregister_ct, product_ct, service_ct, promotion_ct]
)
auth_user_perms = Permission.objects.filter(
    content_type__app_label='auth_api',
    codename__in=['view_user', 'add_user', 'change_user', 'delete_user']
)
client_admin_report_perms = Permission.objects.filter(
    content_type=report_permission_ct,
    codename__in=[
        'view_financial_reports',
        'view_employee_reports',
        'view_sales_reports',
        'view_kpi_dashboard',
        'view_advanced_analytics',
    ]
)
client_admin.permissions.set((admin_perms | client_admin_report_perms | auth_user_perms).distinct())
print(f"✅ Permisos asignados a Client-Admin: {client_admin.permissions.count()}")

# Asignar permisos a Manager
manager = Role.objects.get(name='Manager')
manager_perms = Permission.objects.filter(
    content_type__in=[employee_ct, sale_ct, client_ct, appointment_ct, cashregister_ct, product_ct, service_ct, promotion_ct]
).exclude(
    codename__in=[
        'delete_employee',
        'delete_sale',
        'delete_client',
        'delete_cashregister',
        'delete_product',
        'delete_service',
        'delete_promotion',
    ]
)
manager_report_perms = Permission.objects.filter(
    content_type=report_permission_ct,
    codename__in=[
        'view_employee_reports',
        'view_sales_reports',
        'view_kpi_dashboard',
    ]
)
# Hardening: Manager nunca debe gestionar usuarios auth_api
manager_user_mgmt_perms = Permission.objects.filter(
    content_type__app_label='auth_api',
    codename__in=['add_user', 'change_user', 'delete_user', 'view_user']
)
manager.permissions.set((manager_perms | manager_report_perms).exclude(id__in=manager_user_mgmt_perms.values('id')).distinct())
print(f"✅ Permisos asignados a Manager: {manager.permissions.count()}")

# Asignar permisos a Cajera (operación POS sin gestión administrativa)
cajera = Role.objects.get(name='Cajera')
cajera_perms = Permission.objects.filter(
    content_type__in=[
        sale_ct,
        cashregister_ct,
        promotion_ct,
        client_ct,
        employee_ct,
        product_ct,
        service_ct,
        appointment_ct,
    ],
    codename__in=[
        'add_sale',
        'view_sale',
        'view_cashregister',
        'add_cashregister',
        'view_promotion',
        'view_client',
        'view_employee',
        'view_product',
        'view_service',
        'view_appointment',
        'add_appointment',
        'change_appointment',
    ]
)
cajera.permissions.set(cajera_perms)
print(f"✅ Permisos asignados a Cajera: {cajera_perms.count()}")

# Asignar permisos a Estilista
estilista = Role.objects.get(name='Estilista')
estilista_perms = Permission.objects.filter(
    content_type__in=[client_ct, sale_ct],
    codename__in=['view_client', 'view_sale']
)
estilista.permissions.set(estilista_perms)
print(f"✅ Permisos asignados a Estilista: {estilista_perms.count()}")

print("\n🎉 Configuración completada!")
print("\nPróximos pasos:")
print("1. Ejecutar: python manage.py shell < scripts/sync_user_roles.py")
print("2. Verificar en admin: /admin/roles_api/role/")
