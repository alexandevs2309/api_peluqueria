#!/bin/bash
set -e

# Configuración
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql"

# Crear directorio si no existe
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Iniciando backup..."

# Realizar backup
if pg_dump "$DATABASE_URL" > "$BACKUP_FILE"; then
    echo "[$(date)] Backup completado: $BACKUP_FILE"
    
    # Comprimir backup
    gzip "$BACKUP_FILE"
    echo "[$(date)] Backup comprimido: $BACKUP_FILE.gz"
    
    # Limpiar backups antiguos
    find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    echo "[$(date)] Backups antiguos eliminados (>$RETENTION_DAYS días)"
else
    echo "[$(date)] ERROR: Falló el backup"
    exit 1
fi