#!/bin/bash
# bootstrap.sh - Script para inicialización completa del proyecto

set -euo pipefail

log() {
    echo "[BOOTSTRAP] $1"
}

cleanup() {
    log "Limpiando entorno..."
    docker-compose -f docker-compose-fixed.yml down -v
    docker system prune -f
}

setup_git() {
    log "Configurando Git para line endings..."
    git config core.autocrlf false
    git config core.eol lf
    
    # Normalizar archivos existentes
    find . -name "*.sh" -type f -exec dos2unix {} \; 2>/dev/null || true
}

build_project() {
    log "Construyendo proyecto..."
    docker-compose -f docker-compose-fixed.yml build --no-cache
}

init_database() {
    log "Inicializando base de datos..."
    
    # Esperar a que DB esté lista
    docker-compose -f docker-compose-fixed.yml up -d db redis
    sleep 10
    
    # Ejecutar migraciones en orden específico
    docker-compose -f docker-compose-fixed.yml run --rm web python manage.py migrate auth --no-input
    docker-compose -f docker-compose-fixed.yml run --rm web python manage.py migrate contenttypes --no-input
    docker-compose -f docker-compose-fixed.yml run --rm web python manage.py migrate auth_api --no-input
    docker-compose -f docker-compose-fixed.yml run --rm web python manage.py migrate --no-input
    
    # Crear superusuario solo si se definieron credenciales explícitas
    if [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
        log "Creando superusuario desde variables de entorno..."
        docker-compose -f docker-compose-fixed.yml run --rm \
            -e DJANGO_SUPERUSER_EMAIL \
            -e DJANGO_SUPERUSER_PASSWORD \
            web python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()
email = os.environ['DJANGO_SUPERUSER_EMAIL']
password = os.environ['DJANGO_SUPERUSER_PASSWORD']
if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email, password)
    print('Superusuario creado')
"
    else
        log "Superusuario no creado: define DJANGO_SUPERUSER_EMAIL y DJANGO_SUPERUSER_PASSWORD o usa manage.py createsuperuser."
    fi
}

main() {
    case "${1:-help}" in
        "clean")
            cleanup
            ;;
        "setup")
            setup_git
            build_project
            init_database
            log "Bootstrap completado. Ejecuta: docker-compose -f docker-compose-fixed.yml up"
            ;;
        "reset")
            cleanup
            setup_git
            build_project
            init_database
            log "Reset completado"
            ;;
        *)
            echo "Uso: $0 {clean|setup|reset}"
            echo "  clean - Limpia contenedores y volúmenes"
            echo "  setup - Configuración inicial completa"
            echo "  reset - Limpia y reconfigura todo"
            ;;
    esac
}

main "$@"