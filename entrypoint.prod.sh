#!/bin/bash
# ==========================================
# ENTRYPOINT DE PRODUCCIÓN - SaaS PELUQUERÍAS
# ==========================================

set -euo pipefail

# Colores para logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging con timestamp
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${RED}ERROR: $1${NC}" >&2
    exit 1
}

warning() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${YELLOW}WARNING: $1${NC}"
}

success() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${GREEN}$1${NC}"
}

# ==========================================
# VALIDACIONES CRÍTICAS
# ==========================================

validate_environment() {
    log "🔍 Validando variables de entorno críticas..."
    
    # Variables obligatorias
    local required_vars=(
        "SECRET_KEY"
        "DATABASE_URL"
        "REDIS_URL"
        "CELERY_BROKER_URL"
        "SENTRY_DSN"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            error "Variable de entorno requerida faltante: $var"
        fi
    done
    
    # Validar DEBUG=False
    if [ "${DEBUG:-}" = "True" ]; then
        error "DEBUG debe ser False en producción"
    fi
    
    # Validar SECRET_KEY
    if [ ${#SECRET_KEY} -lt 50 ]; then
        error "SECRET_KEY debe tener al menos 50 caracteres"
    fi
    
    success "Variables de entorno validadas"
}

# ==========================================
# ESPERAR SERVICIOS DEPENDIENTES
# ==========================================

wait_for_service() {
    local host="$1"
    local port="$2"
    local service_name="$3"
    local timeout="${4:-60}"
    
    log "⏳ Esperando $service_name en $host:$port..."
    
    local count=0
    while ! nc -z "$host" "$port"; do
        count=$((count + 1))
        if [ $count -gt $timeout ]; then
            error "Timeout esperando $service_name después de ${timeout}s"
        fi
        sleep 1
    done
    
    success "$service_name está disponible"
}

wait_for_database() {
    log "🗄️ Esperando PostgreSQL..."
    
    # Extraer host y puerto de DATABASE_URL
    local db_host=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    local db_port=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    
    if [ -z "$db_host" ] || [ -z "$db_port" ]; then
        error "No se pudo extraer host/puerto de DATABASE_URL"
    fi
    
    wait_for_service "$db_host" "$db_port" "PostgreSQL" 60
    
    # Verificar conexión con Django
    log "🔌 Verificando conexión a base de datos..."
    python manage.py check --database default --settings=backend.settings_production || \
        error "No se puede conectar a la base de datos"
    
    success "Conexión a base de datos verificada"
}

wait_for_redis() {
    log "🔴 Esperando Redis..."
    
    # Extraer host y puerto de REDIS_URL
    local redis_host=$(echo "$REDIS_URL" | sed -n 's/redis:\/\/\([^:]*\):.*/\1/p')
    local redis_port=$(echo "$REDIS_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    
    if [ -z "$redis_host" ] || [ -z "$redis_port" ]; then
        error "No se pudo extraer host/puerto de REDIS_URL"
    fi
    
    wait_for_service "$redis_host" "$redis_port" "Redis" 30
    
    success "Redis está disponible"
}

# ==========================================
# MIGRACIONES Y SETUP
# ==========================================

run_migrations() {
    log "🔄 Ejecutando migraciones..."
    
    # Verificar migraciones pendientes
    local pending=$(python manage.py showmigrations --plan --settings=backend.settings_production | grep -c "\[ \]" || true)
    
    if [ "$pending" -gt 0 ]; then
        log "📝 $pending migraciones pendientes encontradas"
        python manage.py migrate --settings=backend.settings_production || \
            error "Falló la ejecución de migraciones"
        success "Migraciones ejecutadas exitosamente"
    else
        success "No hay migraciones pendientes"
    fi
}

setup_initial_data() {
    log "🏗️ Configurando datos iniciales..."
    
    # Crear superusuario si no existe (solo en primer despliegue)
    if [ "${CREATE_SUPERUSER:-false}" = "true" ]; then
        python manage.py shell --settings=backend.settings_production << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(
        email='${SUPERUSER_EMAIL:-admin@saaspeluquerias.com}',
        password='${SUPERUSER_PASSWORD:-changeme123}',
        full_name='Super Admin'
    )
    print('Superusuario creado')
else:
    print('Superusuario ya existe')
EOF
    fi
    
    # Crear roles iniciales
    python manage.py shell --settings=backend.settings_production << 'EOF'
try:
    from apps.roles_api.models import Role
    roles = ['SuperAdmin', 'Admin', 'Manager', 'Employee', 'Receptionist']
    for role_name in roles:
        Role.objects.get_or_create(name=role_name)
    print(f'Roles iniciales verificados: {len(roles)}')
except Exception as e:
    print(f'Error creando roles: {e}')
EOF
    
    success "Datos iniciales configurados"
}

# ==========================================
# VALIDACIONES POST-SETUP
# ==========================================

validate_rls() {
    log "🔒 Validando Row Level Security..."
    
    python manage.py shell --settings=backend.settings_production << 'EOF'
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT COUNT(*) 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND rowsecurity = true;
    """)
    rls_count = cursor.fetchone()[0]
    if rls_count < 5:
        raise Exception(f'RLS no está habilitado en suficientes tablas: {rls_count}')
    print(f'RLS validado: {rls_count} tablas protegidas')
EOF
    
    success "RLS validado correctamente"
}

validate_celery_connection() {
    if [[ "$1" == *"celery"* ]]; then
        log "🔄 Validando conexión Celery..."
        
        python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings_production')
import django
django.setup()

from celery import Celery
app = Celery('backend')
app.config_from_object('django.conf:settings', namespace='CELERY')

try:
    inspect = app.control.inspect()
    stats = inspect.stats()
    print('Conexión Celery validada')
except Exception as e:
    raise Exception(f'Error conectando a Celery: {e}')
" || error "No se puede conectar a Celery"
        
        success "Conexión Celery validada"
    fi
}

# ==========================================
# FUNCIÓN PRINCIPAL
# ==========================================

main() {
    log "🚀 Iniciando SaaS Peluquerías - Producción"
    log "Comando: $*"
    
    # Validaciones críticas
    validate_environment
    
    # Esperar servicios dependientes
    wait_for_database
    wait_for_redis
    
    # Solo ejecutar setup en el contenedor web principal
    if [[ "$1" == *"gunicorn"* ]] || [[ "$1" == *"runserver"* ]]; then
        run_migrations
        setup_initial_data
        validate_rls
    fi
    
    # Validaciones específicas por servicio
    validate_celery_connection "$*"
    
    success "Inicialización completada"
    log "🎯 Ejecutando comando: $*"
    
    # Ejecutar comando principal
    exec "$@"
}

# Manejar señales para shutdown graceful
trap 'log "🛑 Recibida señal de shutdown, terminando..."; exit 0' SIGTERM SIGINT

# Ejecutar función principal
main "$@"