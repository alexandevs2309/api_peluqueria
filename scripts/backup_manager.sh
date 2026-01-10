#!/bin/bash
# ==========================================
# ESTRATEGIA DE BACKUPS - SaaS PELUQUERÍAS
# ==========================================

set -euo pipefail

# Configuración
BACKUP_DIR="/backups"
DB_NAME="${DB_NAME:-saas_peluquerias}"
DB_USER="${DB_USER:-saas_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
RETENTION_DAYS=30
S3_BUCKET="${S3_BACKUP_BUCKET:-}"

# Logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
    exit 1
}

# ==========================================
# BACKUP COMPLETO (Diario)
# ==========================================

backup_full() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/full_backup_${timestamp}.sql.gz"
    
    log "Iniciando backup completo..."
    
    # Crear directorio si no existe
    mkdir -p "${BACKUP_DIR}"
    
    # Backup con compresión
    PGPASSWORD="${DB_PASSWORD}" pg_dump \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --verbose \
        --no-password \
        --format=custom \
        --compress=9 \
        --file="${backup_file%.gz}" \
        || error "Falló el backup completo"
    
    # Comprimir
    gzip "${backup_file%.gz}"
    
    # Verificar integridad
    if [ ! -f "${backup_file}" ]; then
        error "Archivo de backup no encontrado: ${backup_file}"
    fi
    
    local size=$(du -h "${backup_file}" | cut -f1)
    log "Backup completo exitoso: ${backup_file} (${size})"
    
    # Subir a S3 si está configurado
    if [ -n "${S3_BUCKET}" ]; then
        upload_to_s3 "${backup_file}" "full/"
    fi
    
    echo "${backup_file}"
}

# ==========================================
# BACKUP INCREMENTAL (Cada 6 horas)
# ==========================================

backup_incremental() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/incremental_backup_${timestamp}.sql.gz"
    
    log "Iniciando backup incremental..."
    
    # Backup solo de cambios recientes (últimas 6 horas)
    PGPASSWORD="${DB_PASSWORD}" pg_dump \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --verbose \
        --no-password \
        --data-only \
        --where="updated_at >= NOW() - INTERVAL '6 hours' OR created_at >= NOW() - INTERVAL '6 hours'" \
        | gzip > "${backup_file}" \
        || error "Falló el backup incremental"
    
    local size=$(du -h "${backup_file}" | cut -f1)
    log "Backup incremental exitoso: ${backup_file} (${size})"
    
    # Subir a S3 si está configurado
    if [ -n "${S3_BUCKET}" ]; then
        upload_to_s3 "${backup_file}" "incremental/"
    fi
    
    echo "${backup_file}"
}

# ==========================================
# BACKUP DE CONFIGURACIÓN
# ==========================================

backup_config() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local config_file="${BACKUP_DIR}/config_backup_${timestamp}.tar.gz"
    
    log "Iniciando backup de configuración..."
    
    # Backup de archivos de configuración críticos
    tar -czf "${config_file}" \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='.git' \
        --exclude='logs/*' \
        --exclude='media/*' \
        --exclude='staticfiles/*' \
        backend/settings*.py \
        .env.production \
        docker-compose*.yml \
        nginx/ \
        scripts/ \
        requirements.txt \
        || error "Falló el backup de configuración"
    
    local size=$(du -h "${config_file}" | cut -f1)
    log "Backup de configuración exitoso: ${config_file} (${size})"
    
    echo "${config_file}"
}

# ==========================================
# SUBIDA A S3
# ==========================================

upload_to_s3() {
    local file_path="$1"
    local s3_prefix="$2"
    local file_name=$(basename "${file_path}")
    
    if [ -z "${S3_BUCKET}" ]; then
        log "S3_BUCKET no configurado, saltando subida"
        return 0
    fi
    
    log "Subiendo ${file_name} a S3..."
    
    aws s3 cp "${file_path}" "s3://${S3_BUCKET}/${s3_prefix}${file_name}" \
        --storage-class STANDARD_IA \
        || error "Falló la subida a S3"
    
    log "Archivo subido exitosamente a S3"
}

# ==========================================
# LIMPIEZA DE BACKUPS ANTIGUOS
# ==========================================

cleanup_old_backups() {
    log "Limpiando backups antiguos (>${RETENTION_DAYS} días)..."
    
    # Limpiar backups locales
    find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete
    find "${BACKUP_DIR}" -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete
    
    # Limpiar backups en S3 (si está configurado)
    if [ -n "${S3_BUCKET}" ]; then
        local cutoff_date=$(date -d "${RETENTION_DAYS} days ago" +%Y-%m-%d)
        aws s3 ls "s3://${S3_BUCKET}/" --recursive | \
        awk -v cutoff="${cutoff_date}" '$1 < cutoff {print $4}' | \
        xargs -I {} aws s3 rm "s3://${S3_BUCKET}/{}"
    fi
    
    log "Limpieza completada"
}

# ==========================================
# VERIFICACIÓN DE BACKUP
# ==========================================

verify_backup() {
    local backup_file="$1"
    
    log "Verificando integridad del backup: ${backup_file}"
    
    # Verificar que el archivo existe y no está vacío
    if [ ! -s "${backup_file}" ]; then
        error "Backup vacío o no encontrado: ${backup_file}"
    fi
    
    # Verificar integridad del archivo comprimido
    if [[ "${backup_file}" == *.gz ]]; then
        gzip -t "${backup_file}" || error "Backup corrupto: ${backup_file}"
    fi
    
    # Verificar que contiene datos de PostgreSQL
    if [[ "${backup_file}" == *.sql.gz ]]; then
        zcat "${backup_file}" | head -10 | grep -q "PostgreSQL" || \
            error "Backup no parece ser de PostgreSQL: ${backup_file}"
    fi
    
    log "Backup verificado exitosamente"
}

# ==========================================
# RESTAURACIÓN DE BACKUP
# ==========================================

restore_backup() {
    local backup_file="$1"
    local target_db="${2:-${DB_NAME}_restore_$(date +%Y%m%d_%H%M%S)}"
    
    log "Iniciando restauración desde: ${backup_file}"
    log "Base de datos destino: ${target_db}"
    
    # Verificar backup antes de restaurar
    verify_backup "${backup_file}"
    
    # Crear base de datos de destino
    PGPASSWORD="${DB_PASSWORD}" createdb \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        "${target_db}" \
        || error "No se pudo crear la base de datos: ${target_db}"
    
    # Restaurar backup
    if [[ "${backup_file}" == *.sql.gz ]]; then
        zcat "${backup_file}" | PGPASSWORD="${DB_PASSWORD}" psql \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d "${target_db}" \
            || error "Falló la restauración"
    else
        PGPASSWORD="${DB_PASSWORD}" pg_restore \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d "${target_db}" \
            --verbose \
            --no-password \
            "${backup_file}" \
            || error "Falló la restauración"
    fi
    
    log "Restauración completada exitosamente en: ${target_db}"
}

# ==========================================
# VALIDACIÓN RLS POST-RESTAURACIÓN
# ==========================================

validate_rls() {
    local db_name="$1"
    
    log "Validando RLS en base de datos: ${db_name}"
    
    # Verificar que RLS está habilitado en tablas críticas
    local rls_check=$(PGPASSWORD="${DB_PASSWORD}" psql \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${db_name}" \
        -t -c "
        SELECT COUNT(*) 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND rowsecurity = true;
    " | tr -d ' ')
    
    if [ "${rls_check}" -lt 5 ]; then
        error "RLS no está habilitado en suficientes tablas (${rls_check})"
    fi
    
    log "RLS validado correctamente (${rls_check} tablas protegidas)"
}

# ==========================================
# FUNCIÓN PRINCIPAL
# ==========================================

main() {
    local action="${1:-full}"
    
    case "${action}" in
        "full")
            backup_file=$(backup_full)
            verify_backup "${backup_file}"
            cleanup_old_backups
            ;;
        "incremental")
            backup_file=$(backup_incremental)
            verify_backup "${backup_file}"
            ;;
        "config")
            backup_file=$(backup_config)
            verify_backup "${backup_file}"
            ;;
        "restore")
            if [ -z "${2:-}" ]; then
                error "Uso: $0 restore <archivo_backup> [base_datos_destino]"
            fi
            restore_backup "$2" "${3:-}"
            validate_rls "${3:-${DB_NAME}_restore_$(date +%Y%m%d_%H%M%S)}"
            ;;
        "cleanup")
            cleanup_old_backups
            ;;
        *)
            echo "Uso: $0 {full|incremental|config|restore|cleanup}"
            echo ""
            echo "Ejemplos:"
            echo "  $0 full                    # Backup completo"
            echo "  $0 incremental             # Backup incremental"
            echo "  $0 config                  # Backup de configuración"
            echo "  $0 restore backup.sql.gz   # Restaurar backup"
            echo "  $0 cleanup                 # Limpiar backups antiguos"
            exit 1
            ;;
    esac
}

# Ejecutar función principal
main "$@"