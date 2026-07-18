#!/bin/bash
set -euo pipefail

# Script para configurar cron job de backups automáticos
# Requiere: DB_USER y DB_NAME en el entorno (o .env.prod)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/backup.sh"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "Configurando cron job para backups automáticos"
echo "Proyecto: $PROJECT_DIR"
echo "Script:   $BACKUP_SCRIPT"
echo "============================================"

if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo "❌ ERROR: No se encuentra $BACKUP_SCRIPT"
    exit 1
fi

if ! command -v crontab &>/dev/null; then
    echo "⚠️  crontab no disponible — instalando cron..."
    apt-get update -qq && apt-get install -y -qq cron 2>/dev/null || yum install -y -q cronie 2>/dev/null || echo "⚠️  No se pudo instalar cron. Instálelo manualmente."
fi

# Crear entrada de cron (backup diario a las 2:00 AM)
CRON_JOB="0 2 * * * cd $PROJECT_DIR && DB_USER=\"\${DB_USER}\" DB_NAME=\"\${DB_NAME}\" $BACKUP_SCRIPT >> $PROJECT_DIR/backups/cron.log 2>&1"

# Agregar al crontab (evitar duplicados)
if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
    echo "⚠️  Ya existe un cron job para backup.sh. Actualizando..."
    (crontab -l 2>/dev/null | grep -v "$BACKUP_SCRIPT"; echo "$CRON_JOB") | crontab -
else
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
fi

echo ""
echo "✅ Cron job configurado correctamente:"
echo "   - Horario:   2:00 AM (diario)"
echo "   - Script:    $BACKUP_SCRIPT"
echo "   - Backup dir: $PROJECT_DIR/backups/"
echo "   - Retención: 30 backups"
echo "   - Log:       $PROJECT_DIR/backups/cron.log"
echo ""
echo "Para verificar: crontab -l"
echo "Para ver logs:  tail -f $PROJECT_DIR/backups/cron.log"
echo ""
echo "⚠️  RECUERDA: Configurar las variables de entorno:"
echo "   export DB_USER=<db_user>"
echo "   export DB_NAME=<db_name>"
echo "   Para producción, añadir estas vars a .env.prod"