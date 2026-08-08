#!/bin/bash

# Configuración
DB_NAME="${POSTGRES_DB:-peluqueria_db}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"
BACKUP_DIR="/backups"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${DATE}.sql.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Crear directorio si no existe
mkdir -p $BACKUP_DIR

# Función de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

# Backup con compresión
log "Iniciando backup de $DB_NAME"
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME --no-password | gzip > $BACKUP_FILE

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h $BACKUP_FILE | cut -f1)
    log "Backup completado: $BACKUP_FILE ($BACKUP_SIZE)"
    
    # Validar backup
    gunzip -t $BACKUP_FILE
    if [ $? -eq 0 ]; then
        log "Backup validado correctamente"
    else
        log "ERROR: Backup corrupto"
        exit 1
    fi
else
    log "ERROR: Fallo en backup"
    exit 1
fi

# Limpiar backups antiguos
find $BACKUP_DIR -name "${DB_NAME}_*.sql.gz" -mtime +$RETENTION_DAYS -delete
log "Limpieza completada - backups > $RETENTION_DAYS días eliminados"

# Enviar métricas (opcional)
echo "backup_success 1" > /tmp/backup_metrics.prom
echo "backup_size_bytes $(stat -c%s $BACKUP_FILE)" >> /tmp/backup_metrics.prom
echo "backup_duration_seconds $SECONDS" >> /tmp/backup_metrics.prom

log "Backup proceso finalizado"