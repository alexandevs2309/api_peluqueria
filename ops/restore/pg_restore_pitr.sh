#!/bin/bash
# pg_restore_pitr.sh - Point-in-Time Recovery
# Ubicación: api_peluqueria/ops/restore/pg_restore_pitr.sh

set -euo pipefail

S3_BUCKET="s3://saas-backups-prod"
RESTORE_DIR="/tmp/restore"
PG_DATA_DIR="/var/lib/postgresql/14/main"
LOG_FILE="/var/log/pg_restore_pitr.log"

exec 1> >(tee -a "${LOG_FILE}")
exec 2>&1

echo "=== PITR INICIADO: $(date) ==="

if [ $# -lt 2 ]; then
    echo "Uso: $0 <BACKUP_TIMESTAMP> <TARGET_TIME>"
    echo "Ejemplo: $0 20240115_020000 '2024-01-15 14:20:00'"
    exit 1
fi

BACKUP_TIMESTAMP=$1
TARGET_TIME=$2

echo "Backup base: ${BACKUP_TIMESTAMP}"
echo "Punto de recuperación: ${TARGET_TIME}"

read -p "⚠️  ¿Continuar con PITR? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "PITR cancelado"
    exit 0
fi

echo "Deteniendo PostgreSQL..."
systemctl stop postgresql || true

echo "Limpiando data directory..."
rm -rf "${PG_DATA_DIR}"/*

echo "Descargando backup base..."
mkdir -p "${RESTORE_DIR}"
aws s3 sync "${S3_BUCKET}/daily/${BACKUP_TIMESTAMP}" "${RESTORE_DIR}/"

echo "Extrayendo backup..."
cd "${PG_DATA_DIR}"
tar -xzf "${RESTORE_DIR}/base.tar.gz"

echo "Configurando PITR..."
touch "${PG_DATA_DIR}/recovery.signal"

cat >> "${PG_DATA_DIR}/postgresql.auto.conf" <<EOF
restore_command = 'aws s3 cp ${S3_BUCKET}/wal/%f %p'
recovery_target_time = '${TARGET_TIME}'
recovery_target_action = 'promote'
EOF

echo "Configurando permisos..."
chown -R postgres:postgres "${PG_DATA_DIR}"
chmod 700 "${PG_DATA_DIR}"

echo "Iniciando recovery..."
systemctl start postgresql

echo "Monitoreando recovery..."
tail -f /var/log/postgresql/postgresql-14-main.log &
TAIL_PID=$!

for i in {1..300}; do
    if pg_isready -q 2>/dev/null; then
        echo "✅ Recovery completado"
        kill $TAIL_PID 2>/dev/null || true
        break
    fi
    if [ $i -eq 300 ]; then
        echo "❌ ERROR: Timeout esperando recovery"
        kill $TAIL_PID 2>/dev/null || true
        exit 1
    fi
    sleep 2
done

echo "Validando punto de recuperación..."
LAST_TIMESTAMP=$(psql -U postgres -t -c "SELECT MAX(created_at) FROM payments;")
echo "Último registro en DB: ${LAST_TIMESTAMP}"
echo "Target esperado: ${TARGET_TIME}"

echo "Limpiando archivos temporales..."
rm -rf "${RESTORE_DIR}"

echo "=== PITR COMPLETADO ==="
