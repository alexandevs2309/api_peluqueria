"""
Script para configurar roles y permisos del sistema RBAC
Ejecutar: python manage.py shell < scripts/setup_roles_permissions.py
"""
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.roles_api.models import Role
from apps.employees_api.models import Employee
from apps.pos_api.models import Sale
from apps.clients_api.models import Client

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
client_ct = ContentType.objects.get_for_model(Client)

# Asignar permisos a Client-Admin (todos)
client_admin = Role.objects.get(name='Client-Admin')
admin_perms = Permission.objects.filter(
    content_type__in=[employee_ct, sale_ct, client_ct]
)
client_admin.permissions.set(admin_perms)
print(f"✅ Permisos asignados a Client-Admin: {admin_perms.count()}")

# Asignar permisos a Manager
manager = Role.objects.get(name='Manager')
manager_perms = Permission.objects.filter(
    content_type__in=[employee_ct, sale_ct, client_ct]
).exclude(
    codename__in=['delete_employee', 'delete_sale', 'delete_client']
)
manager.permissions.set(manager_perms)
print(f"✅ Permisos asignados a Manager: {manager_perms.count()}")

# Asignar permisos a Cajera (solo ventas)
cajera = Role.objects.get(name='Cajera')
cajera_perms = Permission.objects.filter(
    content_type=sale_ct,
    codename__in=['add_sale', 'view_sale']
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
