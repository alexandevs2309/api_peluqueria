#!/bin/bash
# validate_backups.sh - Validación automática de backups
# Ubicación: api_peluqueria/ops/monitoring/validate_backups.sh

set -euo pipefail

S3_BUCKET="s3://saas-backups-prod"
LOG_FILE="/var/log/backup_validation.log"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"

exec 1> >(tee -a "${LOG_FILE}")
exec 2>&1

echo "=== Validación de Backups: $(date) ==="

ERRORS=0

notify() {
    local message=$1
    local status=$2
    echo "${message}"
    if [ -n "${SLACK_WEBHOOK}" ]; then
        curl -X POST "${SLACK_WEBHOOK}" \
            -H 'Content-Type: application/json' \
            -d "{\"text\":\"${status} ${message}\"}" 2>/dev/null || true
    fi
}

# Test 1: Verificar backup de hoy
echo "Test 1: Verificando backup diario..."
TODAY=$(date +%Y%m%d)
if aws s3 ls "${S3_BUCKET}/daily/" | grep -q "${TODAY}"; then
    echo "✅ Backup de hoy encontrado"
else
    notify "❌ ERROR: Backup de hoy no encontrado" "🚨"
    ERRORS=$((ERRORS + 1))
fi

# Test 2: Verificar cantidad de backups
echo "Test 2: Verificando retención..."
DAILY_COUNT=$(aws s3 ls "${S3_BUCKET}/daily/" | wc -l)
WEEKLY_COUNT=$(aws s3 ls "${S3_BUCKET}/weekly/" | wc -l)
MONTHLY_COUNT=$(aws s3 ls "${S3_BUCKET}/monthly/" | wc -l)

echo "Daily backups: ${DAILY_COUNT} (esperado: ~30)"
echo "Weekly backups: ${WEEKLY_COUNT} (esperado: ~13)"
echo "Monthly backups: ${MONTHLY_COUNT} (esperado: ~12)"

if [ "${DAILY_COUNT}" -lt 25 ]; then
    notify "⚠️  WARNING: Pocos backups daily (${DAILY_COUNT})" "⚠️"
fi

# Test 3: Verificar WAL continuidad
echo "Test 3: Verificando WAL archives..."
LAST_WAL=$(aws s3 ls "${S3_BUCKET}/wal/" | tail -1 | awk '{print $1" "$2}')
LAST_WAL_EPOCH=$(date -d "${LAST_WAL}" +%s 2>/dev/null || echo 0)
NOW_EPOCH=$(date +%s)
WAL_AGE=$((NOW_EPOCH - LAST_WAL_EPOCH))

echo "Último WAL: ${LAST_WAL}"
echo "Antigüedad: ${WAL_AGE} segundos"

if [ "${WAL_AGE}" -gt 600 ]; then
    notify "❌ ERROR: Último WAL tiene más de 10 minutos" "🚨"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ WAL archiving funcionando"
fi

# Test 4: Verificar checksums
echo "Test 4: Verificando checksums de últimos 3 backups..."
aws s3 ls "${S3_BUCKET}/daily/" | tail -3 | awk '{print $2}' | while read -r backup; do
    if aws s3 ls "${S3_BUCKET}/daily/${backup}/base.tar.gz.sha256" > /dev/null 2>&1; then
        echo "✅ Checksum existe para ${backup}"
    else
        notify "⚠️  WARNING: Checksum faltante para ${backup}" "⚠️"
    fi
done

# Test 5: Verificar encriptación
echo "Test 5: Verificando encriptación S3..."
ENCRYPTION=$(aws s3api get-bucket-encryption --bucket saas-backups-prod 2>/dev/null | grep -c "AES256" || echo 0)
if [ "${ENCRYPTION}" -gt 0 ]; then
    echo "✅ Encriptación habilitada"
else
    notify "❌ ERROR: Encriptación no habilitada" "🚨"
    ERRORS=$((ERRORS + 1))
fi

# Test 6: Verificar versioning
echo "Test 6: Verificando versioning S3..."
VERSIONING=$(aws s3api get-bucket-versioning --bucket saas-backups-prod | grep -c "Enabled" || echo 0)
if [ "${VERSIONING}" -gt 0 ]; then
    echo "✅ Versioning habilitado"
else
    notify "⚠️  WARNING: Versioning no habilitado" "⚠️"
fi

# Resumen
echo ""
echo "=== RESUMEN ==="
if [ "${ERRORS}" -eq 0 ]; then
    notify "✅ Validación completada: Todos los tests pasaron" "✅"
    exit 0
else
    notify "❌ Validación completada: ${ERRORS} errores encontrados" "🚨"
    exit 1
fi
