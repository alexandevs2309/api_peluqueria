#!/bin/bash
# pg_restore_full.sh - Restore completo de PostgreSQL desde backup
# Ubicación: api_peluqueria/ops/restore/pg_restore_full.sh

set -euo pipefail

S3_BUCKET="s3://saas-backups-prod"
RESTORE_DIR="/tmp/restore"
PG_DATA_DIR="/var/lib/postgresql/14/main"
LOG_FILE="/var/log/pg_restore.log"

exec 1> >(tee -a "${LOG_FILE}")
exec 2>&1

echo "=== RESTORE INICIADO: $(date) ==="

if [ $# -eq 0 ]; then
    echo "Listando backups disponibles:"
    aws s3 ls "${S3_BUCKET}/daily/" | tail -10
    echo ""
    echo "Uso: $0 <TIMESTAMP>"
    echo "Ejemplo: $0 20240115_020000"
    exit 1
fi

BACKUP_TIMESTAMP=$1

echo "Verificando backup: ${BACKUP_TIMESTAMP}"
if ! aws s3 ls "${S3_BUCKET}/daily/${BACKUP_TIMESTAMP}/base.tar.gz" > /dev/null 2>&1; then
    echo "ERROR: Backup no encontrado"
    exit 1
fi

read -p "⚠️  ADVERTENCIA: Esto detendrá PostgreSQL y eliminará datos actuales. ¿Continuar? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Restore cancelado"
    exit 0
fi

echo "Deteniendo PostgreSQL..."
systemctl stop postgresql || true

echo "Limpiando data directory..."
rm -rf "${PG_DATA_DIR}"/*

echo "Creando directorio de restore..."
mkdir -p "${RESTORE_DIR}"

echo "Descargando backup desde S3..."
START_TIME=$(date +%s)
aws s3 sync "${S3_BUCKET}/daily/${BACKUP_TIMESTAMP}" "${RESTORE_DIR}/"
DOWNLOAD_TIME=$(($(date +%s) - START_TIME))
echo "Descarga completada en ${DOWNLOAD_TIME} segundos"

echo "Verificando checksum..."
cd "${RESTORE_DIR}"
if sha256sum -c base.tar.gz.sha256; then
    echo "✅ Checksum válido"
else
    echo "❌ ERROR: Checksum inválido"
    exit 1
fi

echo "Extrayendo backup..."
cd "${PG_DATA_DIR}"
tar -xzf "${RESTORE_DIR}/base.tar.gz"

echo "Configurando permisos..."
chown -R postgres:postgres "${PG_DATA_DIR}"
chmod 700 "${PG_DATA_DIR}"

echo "Configurando recovery..."
touch "${PG_DATA_DIR}/recovery.signal"

cat >> "${PG_DATA_DIR}/postgresql.auto.conf" <<EOF
restore_command = 'aws s3 cp ${S3_BUCKET}/wal/%f %p'
EOF

echo "Iniciando PostgreSQL..."
systemctl start postgresql

echo "Esperando que PostgreSQL esté listo..."
for i in {1..30}; do
    if pg_isready -q; then
        echo "✅ PostgreSQL está listo"
        break
    fi
    echo "Esperando... ($i/30)"
    sleep 2
done

if ! pg_isready -q; then
    echo "❌ ERROR: PostgreSQL no responde"
    exit 1
fi

echo "Validando integridad de datos..."
psql -U postgres -d postgres <<SQL
SELECT 'Tenants: ' || COUNT(*) FROM tenants;
SELECT 'Users: ' || COUNT(*) FROM users;
SELECT 'Subscriptions activas: ' || COUNT(*) FROM subscriptions WHERE status='active';
SELECT 'Último pago: ' || MAX(created_at) FROM payments;
SQL

echo "Limpiando archivos temporales..."
rm -rf "${RESTORE_DIR}"

TOTAL_TIME=$(($(date +%s) - START_TIME))
echo "=== RESTORE COMPLETADO en ${TOTAL_TIME} segundos ==="
echo "Backup restaurado: ${BACKUP_TIMESTAMP}"
