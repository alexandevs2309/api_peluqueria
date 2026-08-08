#!/bin/bash

# Script de restore con validaciones
# Uso: ./restore_db.sh backup_file.sql.gz [target_db_name]

BACKUP_FILE=$1
TARGET_DB=${2:-"${POSTGRES_DB}_restore_$(date +%Y%m%d_%H%M%S)"}
DB_USER="${POSTGRES_USER:-postgres}"
DB_HOST="${POSTGRES_HOST:-db}"
DB_PORT="${POSTGRES_PORT:-5432}"
LOG_FILE="/backups/restore.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

# Validaciones
if [ -z "$BACKUP_FILE" ]; then
    echo "Uso: $0 <backup_file.sql.gz> [target_db_name]"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    log "ERROR: Archivo de backup no encontrado: $BACKUP_FILE"
    exit 1
fi

# Validar integridad del backup
log "Validando integridad del backup..."
gunzip -t "$BACKUP_FILE"
if [ $? -ne 0 ]; then
    log "ERROR: Backup corrupto"
    exit 1
fi

# Crear base de datos temporal
log "Creando base de datos temporal: $TARGET_DB"
createdb -h $DB_HOST -p $DB_PORT -U $DB_USER $TARGET_DB

if [ $? -ne 0 ]; then
    log "ERROR: No se pudo crear la base de datos temporal"
    exit 1
fi

# Restaurar
log "Iniciando restore en $TARGET_DB..."
gunzip -c "$BACKUP_FILE" | psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $TARGET_DB

if [ $? -eq 0 ]; then
    log "Restore completado exitosamente"
    
    # Validar datos básicos
    TABLES_COUNT=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $TARGET_DB -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
    log "Tablas restauradas: $TABLES_COUNT"
    
    echo "Base de datos restaurada como: $TARGET_DB"
    echo "Para usar en producción, ejecuta:"
    echo "1. Detener aplicación"
    echo "2. Renombrar DB actual: ALTER DATABASE $POSTGRES_DB RENAME TO ${POSTGRES_DB}_backup_$(date +%Y%m%d);"
    echo "3. Renombrar DB restaurada: ALTER DATABASE $TARGET_DB RENAME TO $POSTGRES_DB;"
    echo "4. Reiniciar aplicación"
else
    log "ERROR: Fallo en restore"
    dropdb -h $DB_HOST -p $DB_PORT -U $DB_USER $TARGET_DB
    exit 1
fi