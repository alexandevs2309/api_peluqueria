#!/bin/bash
set -e

# Verificar parámetros
if [ $# -eq 0 ]; then
    echo "Uso: $0 <archivo_backup.sql.gz>"
    echo "Ejemplo: $0 ./backups/backup_20241201_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

# Verificar que el archivo existe
if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Archivo no encontrado: $BACKUP_FILE"
    exit 1
fi

echo "[$(date)] Iniciando restore desde: $BACKUP_FILE"

# Descomprimir si es necesario
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "[$(date)] Descomprimiendo archivo..."
    TEMP_FILE="/tmp/restore_$(date +%s).sql"
    gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"
    SQL_FILE="$TEMP_FILE"
else
    SQL_FILE="$BACKUP_FILE"
fi

# Confirmar restore
echo "⚠️  ADVERTENCIA: Esto sobrescribirá la base de datos actual"
read -p "¿Continuar? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelado"
    exit 1
fi

# Realizar restore
echo "[$(date)] Ejecutando restore..."
if psql "$DATABASE_URL" < "$SQL_FILE"; then
    echo "[$(date)] ✅ Restore completado exitosamente"
else
    echo "[$(date)] ❌ ERROR: Falló el restore"
    exit 1
fi

# Limpiar archivo temporal
if [ -n "$TEMP_FILE" ] && [ -f "$TEMP_FILE" ]; then
    rm "$TEMP_FILE"
fi

echo "[$(date)] Proceso completado"