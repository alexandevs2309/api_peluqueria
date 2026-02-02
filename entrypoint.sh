#!/bin/bash
set -euo pipefail

# Variables con defaults seguros
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-postgres}
DB_USER=${DB_USER:-postgres}
MAX_RETRIES=${MAX_RETRIES:-30}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

wait_for_db() {
    log "Esperando DB en $DB_HOST:$DB_PORT..."
    local retries=0
    
    while [ $retries -lt $MAX_RETRIES ]; do
        if nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; then
            log "DB conectada exitosamente"
            return 0
        fi
        retries=$((retries + 1))
        log "Intento $retries/$MAX_RETRIES fallido, reintentando..."
        sleep 2
    done
    
    log "ERROR: No se pudo conectar a DB después de $MAX_RETRIES intentos"
    exit 1
}

setup_django() {
    log "Iniciando setup de Django..."
    
    # Crear migraciones solo si no existen
    log "Creando migraciones..."
    python manage.py makemigrations --no-input
    
    # Aplicar migraciones con orden específico para modelo personalizado
    log "Aplicando migraciones..."
    python manage.py migrate contenttypes --no-input
    python manage.py migrate auth --no-input
    python manage.py migrate auth_api --no-input
    python manage.py migrate tenants_api --no-input
    python manage.py migrate roles_api --no-input
    python manage.py migrate --no-input
    
    log "Setup de Django completado"
}

main() {
    wait_for_db
    
    if [ "${1:-}" = "web" ] || [ "${1:-}" = "python" ]; then
        setup_django
    fi
    
    log "Ejecutando comando: $*"
    exec "$@"
}

main "$@"