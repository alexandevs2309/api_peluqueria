# Script para aplicar migraciones de seguridad en Docker Compose (Windows)

Write-Host "🔐 Aplicando correcciones de seguridad multi-tenant..." -ForegroundColor Cyan

# Paso 1: Backup de base de datos
Write-Host "📦 Creando backup de base de datos..." -ForegroundColor Yellow
$backupFile = "backup_pre_security_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
docker compose exec -T db pg_dump -U postgres -d peluqueria > $backupFile
Write-Host "✅ Backup creado: $backupFile" -ForegroundColor Green

# Paso 2: Verificar conflictos de email
Write-Host "🔍 Verificando emails duplicados en mismo tenant..." -ForegroundColor Yellow
$checkScript = @"
from apps.auth_api.models import User
from django.db.models import Count

duplicates = User.objects.values('email', 'tenant').annotate(count=Count('id')).filter(count__gt=1)
if duplicates.exists():
    print('⚠️  ADVERTENCIA: Emails duplicados encontrados:')
    for dup in duplicates:
        print(f"  - Email: {dup['email']}, Tenant: {dup['tenant']}, Count: {dup['count']}")
    exit(1)
else:
    print('✅ No hay emails duplicados en mismo tenant')
"@

$checkScript | docker compose exec -T web python manage.py shell

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Migración cancelada: resolver conflictos primero" -ForegroundColor Red
    exit 1
}

# Paso 3: Aplicar migraciones
Write-Host "🚀 Aplicando migraciones..." -ForegroundColor Yellow
docker compose exec web python manage.py migrate auth_api

# Paso 4: Verificar migración
Write-Host "✅ Verificando migración..." -ForegroundColor Green
docker compose exec web python manage.py showmigrations auth_api

# Paso 5: Ejecutar tests de seguridad
Write-Host "🧪 Ejecutando tests de seguridad..." -ForegroundColor Yellow
docker compose exec web python manage.py test apps.auth_api.tests_security

Write-Host "✅ Correcciones de seguridad aplicadas exitosamente" -ForegroundColor Green
