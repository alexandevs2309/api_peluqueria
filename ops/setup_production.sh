#!/bin/bash

# Script de setup inicial para producción
# Ejecutar una sola vez en servidor nuevo

set -e

echo "🚀 Configurando entorno de producción..."

# 1. Crear directorios necesarios
sudo mkdir -p /var/log/peluqueria
sudo mkdir -p /backups
sudo mkdir -p /etc/peluqueria

# 2. Configurar permisos
sudo chown -R $USER:$USER /backups
sudo chmod +x ops/backup/backup_db.sh
sudo chmod +x ops/restore/restore_db.sh
sudo chmod +x ops/monitoring/service_monitor.sh

# 3. Configurar variables de entorno
if [ ! -f .env ]; then
    echo "Creando archivo .env..."
    cat > .env << EOF
# Base de datos
POSTGRES_PASSWORD=$(openssl rand -base64 32)
DATABASE_URL=postgresql://postgres:\${POSTGRES_PASSWORD}@db:5432/peluqueria_db

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0

# Django
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,tu-dominio.com

# Alertas
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
ALERT_EMAIL=admin@tuempresa.com

# Sentry (opcional)
SENTRY_DSN=https://your-sentry-dsn

# Versión
APP_VERSION=1.0.0
EOF
    echo "✅ Archivo .env creado - EDITA LAS VARIABLES NECESARIAS"
else
    echo "⚠️  Archivo .env ya existe"
fi

# 4. Configurar cron jobs
echo "Configurando cron jobs..."
(crontab -l 2>/dev/null; echo "0 2 * * * $(pwd)/ops/backup/backup_db.sh >> /var/log/peluqueria/backup.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "*/5 * * * * $(pwd)/ops/monitoring/service_monitor.sh >> /var/log/peluqueria/monitor.log 2>&1") | crontab -

echo "✅ Cron jobs configurados"

# 5. Configurar logrotate
sudo tee /etc/logrotate.d/peluqueria << EOF
/var/log/peluqueria/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
}

/backups/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
}
EOF

echo "✅ Logrotate configurado"

# 6. Configurar firewall básico (si ufw está disponible)
if command -v ufw >/dev/null 2>&1; then
    sudo ufw allow 22/tcp   # SSH
    sudo ufw allow 80/tcp   # HTTP
    sudo ufw allow 443/tcp  # HTTPS
    echo "✅ Firewall configurado"
fi

# 7. Instalar dependencias del sistema
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y curl jq mailutils postgresql-client
elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y curl jq mailx postgresql
fi

echo "✅ Dependencias instaladas"

# 8. Test inicial
echo "🧪 Ejecutando tests iniciales..."

# Test de backup script
if ./ops/backup/backup_db.sh --dry-run 2>/dev/null; then
    echo "✅ Script de backup OK"
else
    echo "⚠️  Script de backup necesita ajustes"
fi

# Test de monitoreo
if ./ops/monitoring/service_monitor.sh --test 2>/dev/null; then
    echo "✅ Script de monitoreo OK"
else
    echo "⚠️  Script de monitoreo necesita ajustes"
fi

echo ""
echo "🎉 Setup completado!"
echo ""
echo "Próximos pasos:"
echo "1. Editar .env con tus configuraciones reales"
echo "2. Configurar webhook de Slack en .env"
echo "3. Ejecutar: docker-compose -f ops/docker-compose.production.yml up -d"
echo "4. Verificar: curl http://localhost/health/"
echo "5. Ejecutar test de backup: ./ops/backup/backup_db.sh"
echo ""
echo "Documentación completa en: ops/PROCEDURES.md"