#!/bin/bash
# pg_backup_daily.sh - Backup diario automatizado de PostgreSQL
# Ubicación: api_peluqueria/ops/backup/pg_backup_daily.sh

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/pg_backup_${TIMESTAMP}"
S3_BUCKET="s3://saas-backups-prod"
RETENTION_DAYS=30
DB_HOST="${DB_HOST:-localhost}"
DB_USER="${DB_USER:-backup_user}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
LOG_FILE="/var/log/pg_backup.log"

exec 1> >(tee -a "${LOG_FILE}")
exec 2>&1

echo "=== Backup iniciado: ${TIMESTAMP} ==="

notify() {
    local message=$1
    local status=$2
    echo "${message}"
    if [ -n "${SLACK_WEBHOOK}" ]; then
        curl -X POST "${SLACK_WEBHOOK}" \
            -H 'Content-Type: application/json' \
            -d "{\"text\":\"${status} Backup ${TIMESTAMP}: ${message}\"}" 2>/dev/null || true
    fi
}

AVAILABLE_SPACE=$(df /tmp | tail -1 | awk '{print $4}')
REQUIRED_SPACE=10485760

if [ "${AVAILABLE_SPACE}" -lt "${REQUIRED_SPACE}" ]; then
    notify "ERROR: Espacio insuficiente en /tmp" "❌"
    exit 1
fi

mkdir -p "${BACKUP_DIR}"

notify "Iniciando pg_basebackup..." "🔄"

if pg_basebackup -h "${DB_HOST}" -U "${DB_USER}" -D "${BACKUP_DIR}" -Ft -z -P -X stream; then
    notify "pg_basebackup completado" "✅"
else
    notify "ERROR: pg_basebackup falló" "❌"
    rm -rf "${BACKUP_DIR}"
    exit 1
fi

cd "${BACKUP_DIR}"
sha256sum base.tar.gz > base.tar.gz.sha256

notify "Subiendo a S3..." "🔄"

if aws s3 sync "${BACKUP_DIR}" "${S3_BUCKET}/daily/${TIMESTAMP}/" \
    --storage-class STANDARD_IA \
    --metadata "backup-date=${TIMESTAMP},backup-type=daily"; then
    notify "Upload a S3 completado" "✅"
else
    notify "ERROR: Upload a S3 falló" "❌"
    rm -rf "${BACKUP_DIR}"
    exit 1
fi

rm -rf "${BACKUP_DIR}"

notify "Limpiando backups antiguos..." "🔄"

aws s3 ls "${S3_BUCKET}/daily/" | awk '{print $2}' | sort | head -n -${RETENTION_DAYS} | \
    while read -r old_backup; do
        aws s3 rm --recursive "${S3_BUCKET}/daily/${old_backup}"
        echo "Eliminado: ${old_backup}"
    done

if aws s3 ls "${S3_BUCKET}/daily/${TIMESTAMP}/base.tar.gz" > /dev/null 2>&1; then
    BACKUP_SIZE=$(aws s3 ls "${S3_BUCKET}/daily/${TIMESTAMP}/" --recursive --summarize | grep "Total Size" | awk '{print $3}')
    notify "Backup completado exitosamente. Tamaño: ${BACKUP_SIZE} bytes" "✅"
else
    notify "ERROR: Verificación de backup falló" "❌"
    exit 1
fi

echo "${TIMESTAMP}" > /var/lib/postgresql/last_backup_success
echo "=== Backup finalizado: $(date +%Y%m%d_%H%M%S) ==="
exit 0
