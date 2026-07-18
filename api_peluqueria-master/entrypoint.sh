#!/bin/bash
set -euo pipefail

MAX_RETRIES=${MAX_RETRIES:-30}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

wait_for_db() {
    log "Esperando disponibilidad de la base de datos..."
    local retries=0

    # Usa Python + psycopg2 para verificar la conexión real.
    # Funciona tanto con DATABASE_URL (Render) como con variables individuales (Docker).
    until python -c "
import os, sys
try:
    import psycopg2
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        conn = psycopg2.connect(db_url, connect_timeout=3)
    else:
        conn = psycopg2.connect(
            dbname=os.environ.get('DB_NAME', 'postgres'),
            user=os.environ.get('DB_USER', 'postgres'),
            password=os.environ.get('DB_PASSWORD', ''),
            host=os.environ.get('DB_HOST', 'db'),
            port=os.environ.get('DB_PORT', '5432'),
            connect_timeout=3,
        )
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; do
        retries=$((retries + 1))
        if [ $retries -ge $MAX_RETRIES ]; then
            log "ERROR: No se pudo conectar a la DB después de $MAX_RETRIES intentos"
            exit 1
        fi
        log "Intento $retries/$MAX_RETRIES fallido, reintentando en 2s..."
        sleep 2
    done

    log "DB disponible"
}

main() {
    # En Render la DB es externa y accesible desde el inicio;
    # el wait solo aplica cuando DB_HOST está definido (Docker local).
    if [ -n "${DB_HOST:-}" ] || [ -n "${DATABASE_URL:-}" ]; then
        wait_for_db
    fi
    log "Ejecutando comando: $*"
    exec "$@"
}

main "$@"
