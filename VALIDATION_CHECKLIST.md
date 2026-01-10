# VALIDACIÓN PRE-DESPLIEGUE - CHECKLIST POR FASES

## 🔴 FASE 1: MULTI-TENANCY (RLS) - **BLOQUEANTE**

### Test 1.1: Aislamiento Cross-Tenant
**OBJETIVO:** Verificar que RLS previene acceso entre tenants
**COMANDO:**
```bash
python manage.py shell -c "
from django.db import connection
from apps.clients_api.models import Client

# Crear datos en tenant 1
with connection.cursor() as cursor:
    cursor.execute(\"SELECT set_config('app.current_tenant_id', '1', true)\")
client1 = Client.objects.create(name='Test T1', email='t1@test.com', tenant_id=1)

# Crear datos en tenant 2  
with connection.cursor() as cursor:
    cursor.execute(\"SELECT set_config('app.current_tenant_id', '2', true)\")
client2 = Client.objects.create(name='Test T2', email='t2@test.com', tenant_id=2)

# Verificar aislamiento T1
with connection.cursor() as cursor:
    cursor.execute(\"SELECT set_config('app.current_tenant_id', '1', true)\")
visible = Client.objects.all().count()
print(f'Tenant 1 ve: {visible} clientes (debe ser 1)')

# Verificar aislamiento T2
with connection.cursor() as cursor:
    cursor.execute(\"SELECT set_config('app.current_tenant_id', '2', true)\")
visible = Client.objects.all().count()
print(f'Tenant 2 ve: {visible} clientes (debe ser 1)')
"
```
**ÉXITO:** Cada tenant ve solo 1 cliente (el suyo)
**FALLO:** Tenant ve > 1 cliente → **NO DESPLEGAR**

### Test 1.2: RLS Activo en Tablas Críticas
**COMANDO:**
```bash
python manage.py shell -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('''
        SELECT tablename, rowsecurity 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename IN ('auth_api_user', 'clients_api_client', 'employees_api_employee')
    ''')
    for table, rls in cursor.fetchall():
        print(f'{table}: RLS={rls}')
"
```
**ÉXITO:** Todas las tablas muestran `RLS=True`
**FALLO:** Alguna tabla con `RLS=False` → **NO DESPLEGAR**

---

## 🟡 FASE 2: HARDENING OPERATIVO - **ADVERTENCIA**

### Test 2.1: Logging Estructurado
**COMANDO:**
```bash
python manage.py shell -c "
import structlog
logger = structlog.get_logger('apps.payroll_api')
logger.info('test_log', employee_id=123, amount='1000.00', tenant_id=1)
print('✅ Log estructurado enviado')
"
```
**ÉXITO:** No hay errores, log aparece en consola/archivo
**FALLO:** Excepción o log no aparece → **ADVERTENCIA**

### Test 2.2: Migraciones Aplicadas
**COMANDO:**
```bash
python manage.py showmigrations --plan | grep '\[ \]'
```
**ÉXITO:** No output (sin migraciones pendientes)
**FALLO:** Muestra migraciones pendientes → **ADVERTENCIA**

### Test 2.3: APIs V2 Compatibles
**COMANDO:**
```bash
curl -s http://localhost:8000/api/payroll/calculations/ | jq '.count'
```
**ÉXITO:** Retorna número >= 0
**FALLO:** Error 500 o estructura incorrecta → **ADVERTENCIA**

---

## 🟢 FASE 3.1: TYPE SAFETY - **INFORMATIVO**

### Test 3.1: MyPy en Servicios Críticos
**COMANDO:**
```bash
mypy apps/payroll_api/services/ apps/utils/models.py
```
**ÉXITO:** `Success: no issues found`
**FALLO:** Errores de tipo → **INFORMATIVO**

---

## 🔴 FASE 3.2: SOFT DELETE + AUDIT - **BLOQUEANTE**

### Test 3.2.1: Soft Delete Funciona
**COMANDO:**
```bash
python manage.py shell -c "
from apps.clients_api.models import Client
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()
client = Client.objects.create(name='Test Delete', email='test@del.com', tenant_id=1)
client_id = client.id

# Soft delete
client.soft_delete(user=user)
print(f'Soft deleted: is_deleted={client.is_deleted}')

# Verificar que no aparece en queryset normal
try:
    Client.objects.get(id=client_id)
    print('❌ FALLO: Cliente visible después de soft delete')
except Client.DoesNotExist:
    print('✅ ÉXITO: Cliente no visible en queryset normal')

# Verificar que existe en all_objects
exists = Client.all_objects.filter(id=client_id).exists()
print(f'Existe en all_objects: {exists}')
"
```
**ÉXITO:** `is_deleted=True`, no visible en queryset normal, existe en all_objects
**FALLO:** Cliente sigue visible o no existe en all_objects → **NO DESPLEGAR**

### Test 3.2.2: Audit Trail Registra
**COMANDO:**
```bash
python manage.py shell -c "
from apps.audit_api.audit_models import BusinessAuditLog, AuditService, AuditAction
from apps.clients_api.models import Client
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()
client = Client.objects.create(name='Test Audit', email='audit@test.com', tenant_id=1)

# Registrar auditoría
AuditService.log_action(
    tenant_id=1,
    actor=user,
    action=AuditAction.CREATE,
    content_object=client
)

# Verificar registro
audit_count = BusinessAuditLog.objects.filter(
    tenant_id=1,
    action=AuditAction.CREATE
).count()
print(f'Registros de auditoría: {audit_count}')
"
```
**ÉXITO:** `audit_count >= 1`
**FALLO:** `audit_count = 0` → **NO DESPLEGAR**

---

## 🟡 FASE 3.3: OPENAPI - **ADVERTENCIA**

### Test 3.3.1: Schema OpenAPI Genera
**COMANDO:**
```bash
curl -s http://localhost:8000/api/schema/ | jq '.info.title'
```
**ÉXITO:** Retorna título de la API
**FALLO:** Error 500 o JSON inválido → **ADVERTENCIA**

### Test 3.3.2: Documentación Accesible
**COMANDO:**
```bash
curl -I http://localhost:8000/api/docs/
```
**ÉXITO:** `HTTP/1.1 200 OK`
**FALLO:** Error 404 o 500 → **ADVERTENCIA**

---

## 🔴 FASE 3.4: PRE-PRODUCCIÓN - **BLOQUEANTE**

### Test 3.4.1: Settings de Producción
**COMANDO:**
```bash
DJANGO_SETTINGS_MODULE=backend.settings_prod python backend/env_validator.py
```
**ÉXITO:** `✅ Validación de entorno: APROBADA`
**FALLO:** Errores críticos → **NO DESPLEGAR**

### Test 3.4.2: Celery Workers Activos
**COMANDO:**
```bash
python manage.py validate_celery
```
**ÉXITO:** `✅ Celery listo para producción`
**FALLO:** Workers inactivos o errores → **NO DESPLEGAR**

### Test 3.4.3: Backup Funciona
**COMANDO:**
```bash
./scripts/backup_strategy.sh validate
```
**ÉXITO:** `✅ Base de datos validada correctamente`
**FALLO:** Errores de conexión o RLS → **NO DESPLEGAR**

---

## 🚦 CHECKLIST FINAL GO/NO-GO

### ✅ EJECUTAR EL DÍA DEL DESPLIEGUE

```bash
#!/bin/bash
# validation_suite.sh - Suite completa de validación

echo "🔍 VALIDACIÓN PRE-DESPLIEGUE"
echo "=========================="

# CRÍTICOS - Si fallan, NO desplegar
echo "🔴 TESTS CRÍTICOS..."

# RLS Isolation
python manage.py shell -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('SELECT COUNT(*) FROM pg_policies WHERE tablename = \'auth_api_user\'')
    policies = cursor.fetchone()[0]
    if policies == 0:
        print('❌ CRÍTICO: Sin políticas RLS')
        exit(1)
    else:
        print('✅ RLS: Políticas activas')
"

# Soft Delete
python manage.py shell -c "
from apps.clients_api.models import Client
test_client = Client.objects.create(name='Test', email='test@test.com', tenant_id=1)
test_client.soft_delete()
if Client.objects.filter(id=test_client.id).exists():
    print('❌ CRÍTICO: Soft delete no funciona')
    exit(1)
else:
    print('✅ SOFT DELETE: Funcionando')
"

# Settings de Producción
if [ "$DJANGO_SETTINGS_MODULE" = "backend.settings_prod" ]; then
    python backend/env_validator.py || exit 1
    echo "✅ SETTINGS: Validados"
else
    echo "❌ CRÍTICO: No está usando settings de producción"
    exit 1
fi

# Celery
python manage.py validate_celery || exit 1

echo ""
echo "🟡 TESTS DE ADVERTENCIA..."

# MyPy
mypy apps/payroll_api/services/ || echo "⚠️ MyPy: Errores de tipo encontrados"

# OpenAPI
curl -s http://localhost:8000/api/schema/ > /dev/null || echo "⚠️ OpenAPI: Schema no accesible"

echo ""
echo "✅ VALIDACIÓN COMPLETADA"
echo "Sistema listo para despliegue"
```

### CRITERIOS FINALES

**🟢 GO - Desplegar:**
- Todos los tests críticos (🔴) pasan
- RLS funciona correctamente
- Soft delete + audit trail operativos
- Settings de producción validados
- Celery activo

**🔴 NO-GO - No desplegar:**
- Cualquier test crítico falla
- RLS permite acceso cross-tenant
- Soft delete no funciona
- Variables de entorno faltantes
- Celery inactivo

**⚠️ EVALUAR - Revisar riesgo:**
- Tests de advertencia fallan
- MyPy reporta errores
- OpenAPI no accesible
- Logs no estructurados