"""
Script para crear SuperAdmin (dueño de la plataforma)
Ejecutar:
  AURON_SUPERADMIN_EMAIL=... AURON_SUPERADMIN_PASSWORD=... \
    python manage.py shell < scripts/create_superadmin.py

No hay contraseña por defecto: las credenciales deben venir del entorno.
"""
import os

from apps.auth_api.models import User

email = os.getenv('AURON_SUPERADMIN_EMAIL', '').strip()
password = os.getenv('AURON_SUPERADMIN_PASSWORD', '')
if not email or not password:
    raise SystemExit(
        'Define AURON_SUPERADMIN_EMAIL y AURON_SUPERADMIN_PASSWORD antes de crear el SuperAdmin.'
    )

try:
    superadmin = User(
        email=email,
        full_name='Platform Admin',
        is_superuser=True,
        is_staff=True,
        is_active=True,
    )
    superadmin.set_password(password)
    superadmin.save(skip_validation=True)
    print(f"✅ SuperAdmin creado: {superadmin.email}")
    print("   Password: definida por AURON_SUPERADMIN_PASSWORD (no se imprime)")
except Exception:
    superadmin = User.objects.get(email=email)
    print(f"ℹ️  SuperAdmin ya existe: {superadmin.email}")

print("\n📊 Detalles:")
print(f"   Email: {superadmin.email}")
print(f"   is_superuser: {superadmin.is_superuser}")
print(f"   is_staff: {superadmin.is_staff}")
print(f"   tenant: {superadmin.tenant}")
print("\n✅ SuperAdmin puede acceder a:")
print("   - /admin/ (Django Admin)")
print("   - Todos los endpoints sin tenant")
print("   - Gestión de roles y permisos")
print("   - Bypass de TenantPermissionByAction")
