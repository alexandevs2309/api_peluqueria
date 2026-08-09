#!/bin/bash
set -euo pipefail

# ============================================================
# Backup script for Auron Suite PostgreSQL database
# Uses docker compose to run pg_dump inside the db container.
# Saves compressed backups to backups/ directory.
# Keeps only the last 30 backups.
# ============================================================

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_COUNT="${RETENTION_COUNT:-30}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/auron_suite_${DATE}.sql.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

log() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "${message}"
    echo "${message}" >> "${LOG_FILE}"
}

# --- Main ---
log "============================================"
log "Iniciando backup de base de datos"
log "Archivo: ${BACKUP_FILE}"

# Run pg_dump via docker compose
if docker compose -f "${COMPOSE_FILE}" exec -T db pg_dump -U "${DB_USER}" -d "${DB_NAME}" 2>> "${LOG_FILE}" | gzip > "${BACKUP_FILE}"; then
    # Get file size
    FILE_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    log "Backup completado exitosamente: ${FILE_SIZE}"
    
    # Verify compressed file integrity
    if gunzip -t "${BACKUP_FILE}" 2>> "${LOG_FILE}"; then
        log "Integridad del backup verificada: OK"
    else
        log "ERROR: El backup comprimido está corrupto"
        rm -f "${BACKUP_FILE}"
        exit 1
    fi
    
    # Cleanup: keep only the last N backups
    log "Limpiando backups antiguos (conservando últimos ${RETENTION_COUNT})..."
    BACKUP_COUNT=$(find "${BACKUP_DIR}" -name "auron_suite_*.sql.gz" -type f | wc -l)
    if [ "${BACKUP_COUNT}" -gt "${RETENTION_COUNT}" ]; then
        REMOVE_COUNT=$((BACKUP_COUNT - RETENTION_COUNT))
        find "${BACKUP_DIR}" -name "auron_suite_*.sql.gz" -type f -printf '%T@ %p\n' \
            | sort -n \
            | head -n "${REMOVE_COUNT}" \
            | while IFS= read -r line; do
                FILE_TO_REMOVE=$(echo "${line}" | cut -d' ' -f2-)
                rm -f "${FILE_TO_REMOVE}"
                log "Eliminado: ${FILE_TO_REMOVE}"
            done
    fi
    log "Backups mantenidos: $(find "${BACKUP_DIR}" -name "auron_suite_*.sql.gz" -type f | wc -l)"
    log "✅ Backup completado exitosamente"
else
    log "❌ ERROR: Falló el backup de base de datos"
    rm -f "${BACKUP_FILE}" 2>/dev/null || true
    exit 1
fi

log "============================================"
