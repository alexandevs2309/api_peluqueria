#!/bin/bash

# Monitor de servicios con alertas básicas
# Ejecutar cada 5 minutos via cron

HEALTH_URL="http://localhost/health/"
WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
EMAIL="${ALERT_EMAIL:-admin@empresa.com}"
LOG_FILE="/var/log/service_monitor.log"
STATE_FILE="/tmp/service_state"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

send_alert() {
    local message="$1"
    local severity="$2"
    
    log "ALERT [$severity]: $message"
    
    # Slack webhook (si está configurado)
    if [ -n "$WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 [$severity] $message\"}" \
            "$WEBHOOK_URL" 2>/dev/null
    fi
    
    # Email básico
    echo "$message" | mail -s "[$severity] Sistema Peluquería" "$EMAIL" 2>/dev/null || true
}

check_service() {
    local service_name="$1"
    local check_command="$2"
    
    if eval "$check_command" >/dev/null 2>&1; then
        echo "ok"
    else
        echo "error"
    fi
}

# Estado anterior
if [ -f "$STATE_FILE" ]; then
    source "$STATE_FILE"
else
    PREV_HEALTH="unknown"
    PREV_DB="unknown"
    PREV_REDIS="unknown"
    PREV_CELERY="unknown"
fi

# Verificaciones actuales
CURRENT_HEALTH=$(check_service "health" "curl -f -s --max-time 10 $HEALTH_URL")
CURRENT_DB=$(check_service "database" "docker exec \$(docker ps -q -f name=db) pg_isready -U postgres")
CURRENT_REDIS=$(check_service "redis" "docker exec \$(docker ps -q -f name=redis) redis-cli ping")
CURRENT_CELERY=$(check_service "celery" "docker exec \$(docker ps -q -f name=celery) celery -A backend inspect active")

# Detectar cambios y alertar
if [ "$PREV_HEALTH" = "ok" ] && [ "$CURRENT_HEALTH" = "error" ]; then
    send_alert "Health endpoint no responde - Sistema posiblemente caído" "CRITICAL"
elif [ "$PREV_HEALTH" = "error" ] && [ "$CURRENT_HEALTH" = "ok" ]; then
    send_alert "Health endpoint recuperado - Sistema operativo" "INFO"
fi

if [ "$PREV_DB" = "ok" ] && [ "$CURRENT_DB" = "error" ]; then
    send_alert "Base de datos PostgreSQL no disponible" "CRITICAL"
elif [ "$PREV_DB" = "error" ] && [ "$CURRENT_DB" = "ok" ]; then
    send_alert "Base de datos PostgreSQL recuperada" "INFO"
fi

if [ "$PREV_REDIS" = "ok" ] && [ "$CURRENT_REDIS" = "error" ]; then
    send_alert "Redis no disponible - Cache y Celery afectados" "HIGH"
elif [ "$PREV_REDIS" = "error" ] && [ "$CURRENT_REDIS" = "ok" ]; then
    send_alert "Redis recuperado" "INFO"
fi

if [ "$PREV_CELERY" = "ok" ] && [ "$CURRENT_CELERY" = "error" ]; then
    send_alert "Celery workers no disponibles - Tareas en background afectadas" "HIGH"
elif [ "$PREV_CELERY" = "error" ] && [ "$CURRENT_CELERY" = "ok" ]; then
    send_alert "Celery workers recuperados" "INFO"
fi

# Verificar error rate alto (últimos 5 minutos)
ERROR_COUNT=$(docker logs --since=5m $(docker ps -q -f name=web) 2>&1 | grep -c "ERROR\|500\|Exception" || echo "0")
if [ "$ERROR_COUNT" -gt 10 ]; then
    send_alert "Error rate alto detectado: $ERROR_COUNT errores en últimos 5 minutos" "HIGH"
fi

# Verificar espacio en disco
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    send_alert "Espacio en disco crítico: ${DISK_USAGE}% usado" "CRITICAL"
elif [ "$DISK_USAGE" -gt 80 ]; then
    send_alert "Espacio en disco alto: ${DISK_USAGE}% usado" "WARNING"
fi

# Guardar estado actual
cat > "$STATE_FILE" << EOF
PREV_HEALTH="$CURRENT_HEALTH"
PREV_DB="$CURRENT_DB"
PREV_REDIS="$CURRENT_REDIS"
PREV_CELERY="$CURRENT_CELERY"
EOF

log "Monitor ejecutado - Health:$CURRENT_HEALTH DB:$CURRENT_DB Redis:$CURRENT_REDIS Celery:$CURRENT_CELERY Disk:${DISK_USAGE}%"