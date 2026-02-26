#!/bin/bash
# Script para aplicar migraciones de seguridad en Docker Compose

echo "🔐 Aplicando correcciones de seguridad multi-tenant..."

# Paso 1: Backup de base de datos
echo "📦 Creando backup de base de datos..."
docker compose exec -T db pg_dump -U postgres -d peluqueria > backup_pre_security_$(date +%Y%m%d_%H%M%S).sql

# Paso 2: Verificar conflictos de email
echo "🔍 Verificando emails duplicados en mismo tenant..."
docker compose exec web python manage.py shell << EOF
from apps.auth_api.models import User
from django.db.models import Count

duplicates = User.objects.values('email', 'tenant').annotate(count=Count('id')).filter(count__gt=1)
if duplicates.exists():
    print("⚠️  ADVERTENCIA: Emails duplicados encontrados:")
    for dup in duplicates:
        print(f"  - Email: {dup['email']}, Tenant: {dup['tenant']}, Count: {dup['count']}")
    print("\n❌ Resolver duplicados antes de continuar")
    exit(1)
else:
    print("✅ No hay emails duplicados en mismo tenant")
EOF

if [ $? -ne 0 ]; then
    echo "❌ Migración cancelada: resolver conflictos primero"
    exit 1
fi

# Paso 3: Aplicar migraciones
echo "🚀 Aplicando migraciones..."
docker compose exec web python manage.py migrate auth_api

# Paso 4: Verificar migración
echo "✅ Verificando migración..."
docker compose exec web python manage.py showmigrations auth_api

# Paso 5: Ejecutar tests de seguridad
echo "🧪 Ejecutando tests de seguridad..."
docker compose exec web python manage.py test apps.auth_api.tests_security

echo "✅ Correcciones de seguridad aplicadas exitosamente"
