from apps.auth_api.models import User
from apps.roles_api.models import UserRole, Role
from django.contrib.auth.models import Permission

print("=== VALIDACIÓN BLINDAJE FINANCIERO ===\n")

# 1. Permisos creados
perms = Permission.objects.filter(content_type__app_label='reports_api')
print(f"✅ Permisos reports_api: {perms.count()}/5")

# 2. Client-Admin tiene permisos
admin_role = Role.objects.get(name='Client-Admin')
admin_perms = admin_role.permissions.filter(content_type__app_label='reports_api')
print(f"✅ Client-Admin: {admin_perms.count()}/5 permisos")

# 3. Cajera NO tiene permisos
cajera_role = Role.objects.get(name='Cajera')
cajera_perms = cajera_role.permissions.filter(content_type__app_label='reports_api')
print(f"✅ Cajera: {cajera_perms.count()}/0 permisos (correcto)")

# 4. Verificar usuarios
cajera_users = User.objects.filter(role='Cajera')
admin_users = User.objects.filter(role='ClientAdmin')
print(f"\n✅ Usuarios Cajera: {cajera_users.count()}")
print(f"✅ Usuarios Admin: {admin_users.count()}")

# 5. Verificar UserRole
if cajera_users.exists():
    cajera = cajera_users.first()
    ur = UserRole.objects.filter(user=cajera, role__name='Cajera').exists()
    print(f"✅ Cajera tiene UserRole: {ur}")

print("\n=== VALIDACIÓN COMPLETADA ===")
