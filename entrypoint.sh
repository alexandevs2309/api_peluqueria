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

main() {
    wait_for_db
    log "Ejecutando comando: $*"
    exec "$@"
}

main "$@"
