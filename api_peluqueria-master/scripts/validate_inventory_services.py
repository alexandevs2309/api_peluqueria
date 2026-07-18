from django.contrib.auth.models import Permission
from apps.roles_api.models import Role

print("=== VALIDACIÓN INVENTARIO Y SERVICIOS ===\n")

# Permisos inventario
inv_perms = Permission.objects.filter(codename='adjust_stock')
print(f"✅ Permiso adjust_stock: {inv_perms.count()}/1")

# Permisos servicios
svc_perms = Permission.objects.filter(codename__in=['set_employee_price', 'assign_employees'])
print(f"✅ Permisos servicios: {svc_perms.count()}/2")

# Client-Admin
admin = Role.objects.get(name='Client-Admin')
admin_inv = admin.permissions.filter(codename='adjust_stock').count()
admin_svc = admin.permissions.filter(codename__in=['set_employee_price', 'assign_employees']).count()
print(f"\n✅ Client-Admin inventario: {admin_inv}/1")
print(f"✅ Client-Admin servicios: {admin_svc}/2")

# Cajera
cajera = Role.objects.get(name='Cajera')
cajera_inv = cajera.permissions.filter(codename='adjust_stock').count()
cajera_svc = cajera.permissions.filter(codename__in=['set_employee_price', 'assign_employees']).count()
print(f"\n✅ Cajera inventario: {cajera_inv}/0 (correcto)")
print(f"✅ Cajera servicios: {cajera_svc}/0 (correcto)")

print("\n=== VALIDACIÓN COMPLETADA ===")
