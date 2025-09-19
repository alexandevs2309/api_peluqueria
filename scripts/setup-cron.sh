#!/bin/bash

# Script para configurar cron job de backups automáticos

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/backup.sh"

echo "Configurando cron job para backups automáticos..."

# Crear entrada de cron (backup diario a las 2:00 AM)
CRON_JOB="0 2 * * * cd $(dirname $SCRIPT_DIR) && $BACKUP_SCRIPT >> /var/log/backup.log 2>&1"

# Agregar al crontab
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Cron job configurado:"
echo "   - Backup diario a las 2:00 AM"
echo "   - Logs en: /var/log/backup.log"
echo "   - Script: $BACKUP_SCRIPT"

echo ""
echo "Para verificar: crontab -l"
echo "Para ver logs: tail -f /var/log/backup.log"