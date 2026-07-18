#!/bin/bash
# generate-secrets.sh - Genera configuración segura automáticamente

set -e

echo "🔐 Generando configuración segura..."

# Generar secretos seguros
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
REDIS_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Crear .env desde template
if [ -f ".env.template" ]; then
    cp .env.template .env
    
    # Reemplazar placeholders con valores reales
    sed -i "s/CHANGE_ME_TO_RANDOM_SECRET_KEY/$SECRET_KEY/g" .env
    sed -i "s/CHANGE_DB_PASSWORD/$DB_PASSWORD/g" .env
    sed -i "s/CHANGE_REDIS_PASSWORD/$REDIS_PASSWORD/g" .env
    
    echo "✅ Archivo .env creado con secretos seguros"
else
    echo "❌ No se encontró .env.template"
    exit 1
fi

# Crear .env.prod desde template
if [ -f ".env.template" ]; then
    cp .env.template .env.prod
    
    # Configuración específica de producción
    sed -i "s/DEBUG=True/DEBUG=False/g" .env.prod
    sed -i "s/ALLOWED_HOSTS=localhost,127.0.0.1/ALLOWED_HOSTS=your-domain.com,api.your-domain.com/g" .env.prod
    sed -i "s/CHANGE_ME_TO_RANDOM_SECRET_KEY/$SECRET_KEY/g" .env.prod
    sed -i "s/CHANGE_DB_PASSWORD/$DB_PASSWORD/g" .env.prod
    sed -i "s/CHANGE_REDIS_PASSWORD/$REDIS_PASSWORD/g" .env.prod
    
    echo "✅ Archivo .env.prod creado para producción"
fi

echo ""
echo "🔑 CREDENCIALES GENERADAS:"
echo "DB Password: $DB_PASSWORD"
echo "Redis Password: $REDIS_PASSWORD"
echo ""
echo "⚠️  IMPORTANTE: Guarda estas credenciales en un lugar seguro"
echo "📝 Los archivos .env están listos para usar"