"""
Script para crear SuperAdmin (dueño de la plataforma)
Ejecutar: python manage.py shell < scripts/create_superadmin.py
"""
from apps.auth_api.models import User

# Crear SuperAdmin sin tenant
superadmin = User(
    email='admin@platform.com',
    full_name='Platform Admin',
    is_superuser=True,
    is_staff=True,
    is_active=True,
)
superadmin.set_password('admin123')

try:
    superadmin.save(skip_validation=True)
    print(f"✅ SuperAdmin creado: {superadmin.email}")
    print(f"   Password: admin123")
    print(f"   ⚠️  CAMBIAR PASSWORD EN PRODUCCIÓN")
except Exception as e:
    # Ya existe
    superadmin = User.objects.get(email='admin@platform.com')
    print(f"ℹ️  SuperAdmin ya existe: {superadmin.email}")

print(f"\n📊 Detalles:")
print(f"   Email: {superadmin.email}")
print(f"   is_superuser: {superadmin.is_superuser}")
print(f"   is_staff: {superadmin.is_staff}")
print(f"   tenant: {superadmin.tenant}")
print(f"\n✅ SuperAdmin puede acceder a:")
print(f"   - /admin/ (Django Admin)")
print(f"   - Todos los endpoints sin tenant")
print(f"   - Gestión de roles y permisos")
print(f"   - Bypass de TenantPermissionByAction")
