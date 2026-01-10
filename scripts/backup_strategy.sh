#!/bin/bash
# scripts/backup_strategy.sh - Estrategia de backups para producción

set -e

# CONFIGURACIÓN DE BACKUPS
BACKUP_DIR="/var/backups/saas-peluquerias"
RETENTION_DAYS=30
DB_NAME="${DATABASE_NAME:-saas_peluquerias}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# FUNCIONES DE BACKUP

backup_database() {
    echo "🔄 Iniciando backup de base de datos..."
    
    # Backup completo con compresión
    pg_dump \
        --host="${DATABASE_HOST}" \
        --port="${DATABASE_PORT:-5432}" \
        --username="${DATABASE_USER}" \
        --dbname="${DB_NAME}" \
        --format=custom \
        --compress=9 \
        --verbose \
        --file="${BACKUP_DIR}/db_backup_${TIMESTAMP}.dump"
    
    echo "✅ Backup completado: db_backup_${TIMESTAMP}.dump"
}

backup_media_files() {
    echo "🔄 Backup de archivos media..."
    
    tar -czf "${BACKUP_DIR}/media_backup_${TIMESTAMP}.tar.gz" \
        -C /app/media .
    
    echo "✅ Media backup completado"
}

cleanup_old_backups() {
    echo "🧹 Limpiando backups antiguos (>${RETENTION_DAYS} días)..."
    
    find "${BACKUP_DIR}" -name "*.dump" -mtime +${RETENTION_DAYS} -delete
    find "${BACKUP_DIR}" -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete
    
    echo "✅ Limpieza completada"
}

verify_backup() {
    local backup_file="$1"
    echo "🔍 Verificando integridad del backup..."
    
    # Verificar que el archivo no está corrupto
    pg_restore --list "${backup_file}" > /dev/null
    
    if [ $? -eq 0 ]; then
        echo "✅ Backup verificado correctamente"
        return 0
    else
        echo "❌ Backup corrupto"
        return 1
    fi
}

# RESTAURACIÓN DE EMERGENCIA
restore_database() {
    local backup_file="$1"
    
    if [ -z "$backup_file" ]; then
        echo "❌ Especifica el archivo de backup"
        echo "Uso: restore_database /path/to/backup.dump"
        return 1
    fi
    
    echo "⚠️ RESTAURANDO BASE DE DATOS DESDE: $backup_file"
    echo "⚠️ Esto SOBRESCRIBIRÁ la base de datos actual"
    read -p "¿Continuar? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "Restauración cancelada"
        return 1
    fi
    
    # Crear base de datos temporal para verificación
    createdb "${DB_NAME}_restore_test"
    
    # Restaurar en base temporal
    pg_restore \
        --host="${DATABASE_HOST}" \
        --port="${DATABASE_PORT:-5432}" \
        --username="${DATABASE_USER}" \
        --dbname="${DB_NAME}_restore_test" \
        --verbose \
        "${backup_file}"
    
    if [ $? -eq 0 ]; then
        echo "✅ Verificación de restauración exitosa"
        
        # Intercambiar bases de datos
        psql -c "ALTER DATABASE ${DB_NAME} RENAME TO ${DB_NAME}_old;"
        psql -c "ALTER DATABASE ${DB_NAME}_restore_test RENAME TO ${DB_NAME};"
        
        echo "✅ Restauración completada"
        echo "⚠️ Base de datos anterior renombrada a: ${DB_NAME}_old"
    else
        echo "❌ Error en restauración"
        dropdb "${DB_NAME}_restore_test"
        return 1
    fi
}

# VALIDACIONES PRE-PRODUCCIÓN
validate_database_setup() {
    echo "🔍 Validando configuración de base de datos..."
    
    # Verificar conexión
    psql -c "SELECT version();" > /dev/null
    if [ $? -ne 0 ]; then
        echo "❌ No se puede conectar a la base de datos"
        return 1
    fi
    
    # Verificar RLS
    rls_status=$(psql -t -c "SELECT current_setting('row_security');")
    if [ "$rls_status" != " on" ]; then
        echo "❌ Row Level Security NO está activo"
        return 1
    fi
    
    # Verificar migraciones
    python manage.py showmigrations --plan | grep '\[ \]'
    if [ $? -eq 0 ]; then
        echo "❌ Hay migraciones pendientes"
        return 1
    fi
    
    # Verificar políticas RLS críticas
    policies_count=$(psql -t -c "SELECT COUNT(*) FROM pg_policies WHERE tablename IN ('auth_api_user', 'clients_api_client', 'employees_api_employee');")
    if [ "$policies_count" -lt 3 ]; then
        echo "❌ Políticas RLS faltantes en tablas críticas"
        return 1
    fi
    
    echo "✅ Base de datos validada correctamente"
    return 0
}

# EJECUCIÓN PRINCIPAL
case "$1" in
    "backup")
        mkdir -p "${BACKUP_DIR}"
        backup_database
        backup_media_files
        cleanup_old_backups
        ;;
    "restore")
        restore_database "$2"
        ;;
    "validate")
        validate_database_setup
        ;;
    "verify")
        verify_backup "$2"
        ;;
    *)
        echo "Uso: $0 {backup|restore|validate|verify}"
        echo ""
        echo "Comandos:"
        echo "  backup          - Crear backup completo"
        echo "  restore <file>  - Restaurar desde backup"
        echo "  validate        - Validar configuración DB"
        echo "  verify <file>   - Verificar integridad backup"
        exit 1
        ;;
esac