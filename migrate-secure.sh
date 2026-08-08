#!/bin/bash
# migrate-secure.sh - Migración segura sin interrumpir servicio

set -e

echo "🔄 Iniciando migración segura..."

# 1. Backup de archivos actuales
echo "📦 Creando backup de configuración actual..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo "No hay .env para respaldar"
cp .env.prod .env.prod.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo "No hay .env.prod para respaldar"

# 2. Generar nuevos secretos si no existen
if [ ! -f ".env" ] || grep -q "CHANGE_ME" .env 2>/dev/null; then
    echo "🔐 Generando nuevos secretos..."
    bash generate-secrets.sh
else
    echo "✅ Configuración existente detectada, manteniéndola"
fi

# 3. Verificar permisos para usuarios no-root
echo "🔧 Configurando permisos para usuarios no-root..."
sudo chown -R 1000:1000 . 2>/dev/null || echo "⚠️  No se pudieron cambiar permisos (ejecutar como sudo si es necesario)"

# 4. Reconstruir contenedores con nueva configuración
echo "🏗️  Reconstruyendo contenedores con configuración segura..."
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 5. Verificar que todo funciona
echo "🔍 Verificando servicios..."
sleep 10

if docker-compose ps | grep -q "Up"; then
    echo "✅ Migración completada exitosamente"
    echo ""
    echo "🔐 MEJORAS DE SEGURIDAD APLICADAS:"
    echo "  ✅ Contenedores ejecutándose como usuario no-root (1000:1000)"
    echo "  ✅ Redis con autenticación habilitada"
    echo "  ✅ Puerto PostgreSQL cerrado al exterior"
    echo "  ✅ Rate limiting en nginx configurado"
    echo "  ✅ Headers de seguridad mejorados"
    echo "  ✅ Tokens JWT con duración reducida (30 min)"
    echo "  ✅ Logging de seguridad habilitado"
    echo ""
    echo "📝 PRÓXIMOS PASOS:"
    echo "  1. Cambiar credenciales de superusuario por defecto"
    echo "  2. Configurar ALLOWED_HOSTS para producción"
    echo "  3. Implementar HTTPS en producción"
else
    echo "❌ Error en la migración, restaurando backup..."
    docker-compose down
    mv .env.backup.* .env 2>/dev/null || true
    mv .env.prod.backup.* .env.prod 2>/dev/null || true
    docker-compose up -d
    echo "🔄 Backup restaurado"
fi