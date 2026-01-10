#!/bin/bash
# validation_suite.sh - Suite completa de validación pre-despliegue

set -e

echo "🔍 VALIDACIÓN PRE-DESPLIEGUE SaaS PELUQUERÍAS"
echo "============================================="
echo ""

CRITICAL_FAILURES=0
WARNING_COUNT=0

# Función para tests críticos
critical_test() {
    local test_name="$1"
    local command="$2"
    
    echo "🔴 CRÍTICO: $test_name"
    if eval "$command"; then
        echo "   ✅ PASS"
    else
        echo "   ❌ FAIL - BLOQUEANTE"
        CRITICAL_FAILURES=$((CRITICAL_FAILURES + 1))
    fi
    echo ""
}

# Función para tests de advertencia
warning_test() {
    local test_name="$1" 
    local command="$2"
    
    echo "🟡 ADVERTENCIA: $test_name"
    if eval "$command"; then
        echo "   ✅ PASS"
    else
        echo "   ⚠️ FAIL - Revisar"
        WARNING_COUNT=$((WARNING_COUNT + 1))
    fi
    echo ""
}

echo "EJECUTANDO TESTS CRÍTICOS..."
echo "============================="

# Test 1: RLS Políticas Activas
critical_test "RLS Políticas Activas" "
python manage.py shell -c \"
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('SELECT COUNT(*) FROM pg_policies WHERE tablename IN (\'auth_api_user\', \'clients_api_client\')')
    policies = cursor.fetchone()[0]
    if policies < 2:
        exit(1)
    print(f'Políticas RLS encontradas: {policies}')
\"
"

# Test 2: Aislamiento Multi-tenant
critical_test "Aislamiento Multi-tenant" "
python manage.py shell -c \"
from django.db import connection
from apps.clients_api.models import Client

# Limpiar datos de prueba
Client.all_objects.filter(email__contains='validation_test').delete()

# Crear datos en tenant 1
with connection.cursor() as cursor:
    cursor.execute('SELECT set_config(\\\"app.current_tenant_id\\\", \\\"1\\\", true)')
client1 = Client.objects.create(name='Test T1', email='validation_test_t1@test.com', tenant_id=1)

# Crear datos en tenant 2
with connection.cursor() as cursor:
    cursor.execute('SELECT set_config(\\\"app.current_tenant_id\\\", \\\"2\\\", true)')
client2 = Client.objects.create(name='Test T2', email='validation_test_t2@test.com', tenant_id=2)

# Verificar aislamiento T1
with connection.cursor() as cursor:
    cursor.execute('SELECT set_config(\\\"app.current_tenant_id\\\", \\\"1\\\", true)')
visible_t1 = Client.objects.filter(email__contains='validation_test').count()

# Verificar aislamiento T2  
with connection.cursor() as cursor:
    cursor.execute('SELECT set_config(\\\"app.current_tenant_id\\\", \\\"2\\\", true)')
visible_t2 = Client.objects.filter(email__contains='validation_test').count()

print(f'Tenant 1 ve: {visible_t1}, Tenant 2 ve: {visible_t2}')

if visible_t1 != 1 or visible_t2 != 1:
    exit(1)
\"
"

# Test 3: Soft Delete Funcional
critical_test "Soft Delete Funcional" "
python manage.py shell -c \"
from apps.clients_api.models import Client
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()

if not user:
    print('Creando usuario de prueba...')
    user = User.objects.create_user(email='test@validation.com', password='test123', tenant_id=1)

client = Client.objects.create(name='Test Delete', email='validation_delete@test.com', tenant_id=1)
client_id = client.id

# Soft delete
client.soft_delete(user=user)

# Verificar que no aparece en queryset normal
if Client.objects.filter(id=client_id).exists():
    print('FALLO: Cliente visible después de soft delete')
    exit(1)

# Verificar que existe en all_objects
if not Client.all_objects.filter(id=client_id).exists():
    print('FALLO: Cliente no existe en all_objects')
    exit(1)

print('Soft delete funcionando correctamente')
\"
"

# Test 4: Settings de Producción
if [ "$DJANGO_SETTINGS_MODULE" = "backend.settings_prod" ]; then
    critical_test "Settings de Producción" "python backend/env_validator.py"
else
    echo "🔴 CRÍTICO: Settings de Producción"
    echo "   ❌ FAIL - No está usando backend.settings_prod"
    CRITICAL_FAILURES=$((CRITICAL_FAILURES + 1))
    echo ""
fi

# Test 5: Migraciones Aplicadas
critical_test "Migraciones Aplicadas" "
migrations_pending=\$(python manage.py showmigrations --plan | grep '\\[ \\]' | wc -l)
if [ \$migrations_pending -gt 0 ]; then
    echo \"Migraciones pendientes: \$migrations_pending\"
    exit 1
fi
echo 'Todas las migraciones aplicadas'
"

echo "EJECUTANDO TESTS DE ADVERTENCIA..."
echo "=================================="

# Test 6: MyPy Type Safety
warning_test "MyPy Type Safety" "
mypy apps/utils/models.py apps/audit_api/audit_models.py --ignore-missing-imports
"

# Test 7: OpenAPI Schema
warning_test "OpenAPI Schema" "
curl -s http://localhost:8000/api/schema/ | jq '.info.title' > /dev/null
"

# Test 8: Logging Estructurado
warning_test "Logging Estructurado" "
python manage.py shell -c \"
import structlog
logger = structlog.get_logger('validation_test')
logger.info('test_validation', test_id=12345)
print('Logging estructurado funcionando')
\"
"

echo "RESUMEN DE VALIDACIÓN"
echo "===================="

if [ $CRITICAL_FAILURES -gt 0 ]; then
    echo "❌ RESULTADO: NO-GO"
    echo "   Fallos críticos: $CRITICAL_FAILURES"
    echo "   🚫 NO DESPLEGAR - Corregir fallos críticos primero"
    exit 1
elif [ $WARNING_COUNT -gt 0 ]; then
    echo "⚠️ RESULTADO: EVALUAR"
    echo "   Advertencias: $WARNING_COUNT"
    echo "   ⚠️ Revisar advertencias antes de desplegar"
    exit 2
else
    echo "✅ RESULTADO: GO"
    echo "   Todos los tests críticos: PASS"
    echo "   Advertencias: 0"
    echo "   🚀 LISTO PARA DESPLEGAR"
    exit 0
fi