#!/bin/bash
# backup-production.sh - Sistema de backup automatizado para producción

set -euo pipefail

# Configuración
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_BUCKET="${S3_BUCKET:-}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"

# Colores para logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    notify_slack "❌ Backup failed: $1"
    exit 1
}

notify_slack() {
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$1\"}" \
            "$SLACK_WEBHOOK" || true
    fi
}

# Crear directorio de backup
mkdir -p "$BACKUP_DIR"

# Timestamp para archivos
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

log "🚀 Iniciando backup automatizado..."

# 1. Backup de Base de Datos
log "📊 Creando backup de PostgreSQL..."
DB_BACKUP="$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

docker-compose exec -T db pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$DB_BACKUP" || error "Falló backup de base de datos"

log "✅ Backup de DB creado: $(basename "$DB_BACKUP")"

# 2. Backup de Redis
log "🔴 Creando backup de Redis..."
REDIS_BACKUP="$BACKUP_DIR/redis_backup_$TIMESTAMP.rdb"

docker-compose exec -T redis redis-cli --rdb - > "$REDIS_BACKUP" || warn "Falló backup de Redis"

# 3. Backup de archivos media
log "📁 Creando backup de archivos media..."
MEDIA_BACKUP="$BACKUP_DIR/media_backup_$TIMESTAMP.tar.gz"

tar -czf "$MEDIA_BACKUP" -C . media/ staticfiles/ || warn "Falló backup de media"

# 4. Backup de configuración
log "⚙️ Creando backup de configuración..."
CONFIG_BACKUP="$BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz"

tar -czf "$CONFIG_BACKUP" \
    docker-compose.yml \
    docker-compose.prod.yml \
    nginx/nginx.conf \
    .env.prod \
    requirements.txt || warn "Falló backup de configuración"

# 5. Crear manifest del backup
MANIFEST="$BACKUP_DIR/backup_manifest_$TIMESTAMP.json"
cat > "$MANIFEST" << EOF
{
    "timestamp": "$TIMESTAMP",
    "date": "$(date -Iseconds)",
    "files": {
        "database": "$(basename "$DB_BACKUP")",
        "redis": "$(basename "$REDIS_BACKUP")",
        "media": "$(basename "$MEDIA_BACKUP")",
        "config": "$(basename "$CONFIG_BACKUP")"
    },
    "sizes": {
        "database": "$(du -h "$DB_BACKUP" | cut -f1)",
        "redis": "$(du -h "$REDIS_BACKUP" | cut -f1)",
        "media": "$(du -h "$MEDIA_BACKUP" | cut -f1)",
        "config": "$(du -h "$CONFIG_BACKUP" | cut -f1)"
    },
    "total_size": "$(du -sh "$BACKUP_DIR"/*_$TIMESTAMP.* | awk '{sum+=$1} END {print sum "B"}')"
}
EOF

# 6. Subir a S3 (si está configurado)
if [ -n "$S3_BUCKET" ]; then
    log "☁️ Subiendo backups a S3..."
    
    aws s3 cp "$DB_BACKUP" "s3://$S3_BUCKET/backups/$(date +%Y/%m/%d)/" || warn "Falló subida de DB a S3"
    aws s3 cp "$REDIS_BACKUP" "s3://$S3_BUCKET/backups/$(date +%Y/%m/%d)/" || warn "Falló subida de Redis a S3"
    aws s3 cp "$MEDIA_BACKUP" "s3://$S3_BUCKET/backups/$(date +%Y/%m/%d)/" || warn "Falló subida de media a S3"
    aws s3 cp "$CONFIG_BACKUP" "s3://$S3_BUCKET/backups/$(date +%Y/%m/%d)/" || warn "Falló subida de config a S3"
    aws s3 cp "$MANIFEST" "s3://$S3_BUCKET/backups/$(date +%Y/%m/%d)/" || warn "Falló subida de manifest a S3"
    
    log "✅ Backups subidos a S3"
fi

# 7. Limpiar backups antiguos
log "🧹 Limpiando backups antiguos (>$RETENTION_DAYS días)..."
find "$BACKUP_DIR" -name "*backup_*" -type f -mtime +$RETENTION_DAYS -delete || warn "Falló limpieza de backups antiguos"

# 8. Verificar integridad del backup
log "🔍 Verificando integridad del backup..."
if gzip -t "$DB_BACKUP"; then
    log "✅ Backup de DB íntegro"
else
    error "❌ Backup de DB corrupto"
fi

# 9. Estadísticas finales
TOTAL_SIZE=$(du -sh "$BACKUP_DIR"/*_$TIMESTAMP.* | awk '{sum+=$1} END {print sum}')
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/*_$TIMESTAMP.* | wc -l)

log "📊 Backup completado exitosamente:"
log "   - Archivos creados: $BACKUP_COUNT"
log "   - Tamaño total: $TOTAL_SIZE"
log "   - Ubicación: $BACKUP_DIR"

# 10. Notificar éxito
notify_slack "✅ Backup completado exitosamente - $BACKUP_COUNT archivos, $TOTAL_SIZE total"

log "🎉 Backup automatizado completado!"