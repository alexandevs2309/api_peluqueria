"""
Script para sincronizar User.role → UserRole
Ejecutar: python manage.py shell < scripts/sync_user_roles.py
"""
from apps.auth_api.models import User
from apps.roles_api.models import Role, UserRole

print("🔄 Sincronizando User.role → UserRole...")

synced = 0
skipped = 0
errors = 0

for user in User.objects.filter(role__isnull=False).exclude(is_superuser=True):
    if not user.tenant:
        print(f"⚠️  Usuario sin tenant: {user.email}")
        skipped += 1
        continue
    
    try:
        role = Role.objects.get(name=user.role)
        user_role, created = UserRole.objects.get_or_create(
            user=user,
            role=role,
            tenant=user.tenant
        )
        if created:
            print(f"✅ {user.email} → {role.name} en {user.tenant.name}")
            synced += 1
        else:
            print(f"ℹ️  Ya existe: {user.email} → {role.name}")
            skipped += 1
    except Role.DoesNotExist:
        print(f"❌ Rol no existe: '{user.role}' para {user.email}")
        errors += 1

print(f"\n📊 Resumen:")
print(f"   Sincronizados: {synced}")
print(f"   Ya existían: {skipped}")
print(f"   Errores: {errors}")

if errors > 0:
    print(f"\n⚠️  Hay {errors} usuarios con roles no válidos")
    print("   Ejecutar: python manage.py shell < scripts/setup_roles_permissions.py")
