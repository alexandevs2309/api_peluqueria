#!/bin/bash

# 🚀 Script de despliegue para PRODUCCIÓN con Docker
# Configura permisos y directorios para contenedores no-root

set -e

echo "🚀 Preparando despliegue de producción..."

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.prod.yml" ]; then
    error "No se encontró docker-compose.prod.yml. Ejecuta desde api_peluqueria-master/"
fi

# 1. Verificar archivo .env.prod
if [ ! -f ".env.prod" ]; then
    warn "Archivo .env.prod no encontrado. Copiando desde .env.production.example..."
    cp .env.production.example .env.prod
    warn "⚠️  IMPORTANTE: Edita .env.prod con configuraciones de producción"
fi

# 2. Crear directorios con permisos correctos
log "📁 Creando directorios para producción..."

# Crear directorios si no existen
mkdir -p media/products
mkdir -p staticfiles

# Asignar permisos para usuario 1000:1000 (contenedor no-root)
log "🔐 Configurando permisos para contenedores no-root..."
sudo chown -R 1000:1000 media/
sudo chown -R 1000:1000 staticfiles/
sudo chmod -R 755 media/
sudo chmod -R 755 staticfiles/

# 3. Construir imágenes
log "🏗️  Construyendo imágenes Docker..."
docker compose -f docker-compose.prod.yml build

# 4. Ejecutar migraciones
log "📊 Ejecutando migraciones..."
docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate

# 5. Recopilar archivos estáticos
log "📦 Recopilando archivos estáticos..."
docker compose -f docker-compose.prod.yml run --rm web python manage.py collectstatic --noinput

# 6. Crear superusuario si no existe (sin contraseña por defecto)
if [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    log "👤 Configurando superusuario desde variables de entorno..."
    docker compose -f docker-compose.prod.yml run --rm \
        -e DJANGO_SUPERUSER_EMAIL \
        -e DJANGO_SUPERUSER_PASSWORD \
        web python manage.py shell -c "
import os
from apps.auth_api.models import User
email = os.environ['DJANGO_SUPERUSER_EMAIL']
password = os.environ['DJANGO_SUPERUSER_PASSWORD']
if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email, password, role='SuperAdmin')
    print('Superusuario creado')
else:
    print('Superusuario ya existe')
"
else
    warn "No se creó superusuario: define DJANGO_SUPERUSER_EMAIL y DJANGO_SUPERUSER_PASSWORD en .env.prod, o crea el usuario con manage.py createsuperuser."
fi

# 7. Verificar permisos finales
log "🔍 Verificando permisos finales..."
ls -la media/
ls -la staticfiles/

echo ""
echo " Preparación de producción completada!"
echo ""
echo " Para iniciar en producción:"
echo "   docker compose -f docker-compose.prod.yml up -d"
echo ""
echo " Para monitorear:"
echo "   docker compose -f docker-compose.prod.yml logs -f"
echo ""
echo " Para detener:"
echo "   docker compose -f docker-compose.prod.yml down"
echo ""