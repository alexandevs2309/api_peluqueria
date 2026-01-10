#!/bin/bash
# ==========================================
# VALIDACIÓN FINAL PRE-DESPLIEGUE
# SaaS Peluquerías - Fase 3.4
# ==========================================

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Contadores
PASSED=0
FAILED=0
WARNINGS=0

# Logging
log() {
    echo -e "[$(date '+%H:%M:%S')] $1"
}

success() {
    echo -e "[$(date '+%H:%M:%S')] ${GREEN}✅ $1${NC}"
    ((PASSED++))
}

error() {
    echo -e "[$(date '+%H:%M:%S')] ${RED}❌ $1${NC}"
    ((FAILED++))
}

warning() {
    echo -e "[$(date '+%H:%M:%S')] ${YELLOW}⚠️ $1${NC}"
    ((WARNINGS++))
}

info() {
    echo -e "[$(date '+%H:%M:%S')] ${BLUE}ℹ️ $1${NC}"
}

# ==========================================
# BANNER
# ==========================================
print_banner() {
    echo -e "${BLUE}"
    echo "=================================================="
    echo "🚀 VALIDACIÓN FINAL PRE-DESPLIEGUE"
    echo "   SaaS Peluquerías - Fase 3.4"
    echo "=================================================="
    echo -e "${NC}"
}

# ==========================================
# VALIDACIONES
# ==========================================

validate_environment() {
    info "🔍 Validando variables de entorno..."
    
    if [ ! -f ".env.production" ]; then
        error "Archivo .env.production no encontrado"
        return
    fi
    
    # Ejecutar validador de entorno
    if python scripts/validate_env.py --env-file .env.production > /dev/null 2>&1; then
        success "Variables de entorno válidas"
    else
        error "Variables de entorno inválidas"
        python scripts/validate_env.py --env-file .env.production
    fi
}

validate_django_config() {
    info "⚙️ Validando configuración Django..."
    
    # Check general
    if python manage.py check --settings=backend.settings_production > /dev/null 2>&1; then
        success "Configuración Django válida"
    else
        error "Configuración Django inválida"
        python manage.py check --settings=backend.settings_production
        return
    fi
    
    # Check de despliegue
    if python manage.py check --deploy --settings=backend.settings_production > /dev/null 2>&1; then
        success "Configuración de despliegue válida"
    else
        error "Configuración de despliegue inválida"
        python manage.py check --deploy --settings=backend.settings_production
    fi
    
    # Check de seguridad
    if python manage.py check --tag security --settings=backend.settings_production > /dev/null 2>&1; then
        success "Configuración de seguridad válida"
    else
        warning "Advertencias de seguridad encontradas"
        python manage.py check --tag security --settings=backend.settings_production
    fi
}

validate_database() {
    info "🗄️ Validando base de datos..."
    
    # Verificar conexión
    if python manage.py check --database default --settings=backend.settings_production > /dev/null 2>&1; then
        success "Conexión a base de datos exitosa"
    else
        error "No se puede conectar a la base de datos"
        return
    fi
    
    # Verificar migraciones
    local pending=$(python manage.py showmigrations --plan --settings=backend.settings_production | grep -c "\[ \]" || true)
    if [ "$pending" -eq 0 ]; then
        success "No hay migraciones pendientes"
    else
        warning "$pending migraciones pendientes (se aplicarán en despliegue)"
    fi
}

validate_static_files() {
    info "📁 Validando archivos estáticos..."
    
    if python manage.py collectstatic --dry-run --noinput --settings=backend.settings_production > /dev/null 2>&1; then
        success "Archivos estáticos válidos"
    else
        error "Error en archivos estáticos"
        python manage.py collectstatic --dry-run --noinput --settings=backend.settings_production
    fi
}

validate_docker() {
    info "🐳 Validando Docker..."
    
    # Verificar docker-compose
    if [ ! -f "docker-compose.prod.yml" ]; then
        error "docker-compose.prod.yml no encontrado"
        return
    fi
    
    # Validar sintaxis
    if docker-compose -f docker-compose.prod.yml config > /dev/null 2>&1; then
        success "docker-compose.prod.yml válido"
    else
        error "docker-compose.prod.yml inválido"
        docker-compose -f docker-compose.prod.yml config
        return
    fi
    
    # Verificar Dockerfile
    if [ ! -f "Dockerfile.prod" ]; then
        error "Dockerfile.prod no encontrado"
        return
    fi
    
    success "Archivos Docker válidos"
}

validate_security() {
    info "🔒 Validando configuración de seguridad..."
    
    # Verificar DEBUG=False
    if grep -q "DEBUG.*=.*False" backend/settings_production.py; then
        success "DEBUG=False confirmado"
    else
        error "DEBUG debe ser False en producción"
    fi
    
    # Verificar SECRET_KEY no por defecto
    if grep -q "django-insecure" .env.production 2>/dev/null; then
        error "SECRET_KEY por defecto detectado"
    else
        success "SECRET_KEY personalizado"
    fi
    
    # Verificar ALLOWED_HOSTS
    if grep -q "ALLOWED_HOSTS.*=.*\*" backend/settings_production.py; then
        error "ALLOWED_HOSTS no debe contener '*'"
    else
        success "ALLOWED_HOSTS configurado correctamente"
    fi
}

validate_external_services() {
    info "🌐 Validando servicios externos..."
    
    # Verificar variables de Sentry
    if grep -q "SENTRY_DSN" .env.production; then
        success "Sentry configurado"
    else
        warning "Sentry no configurado"
    fi
    
    # Verificar SendGrid
    if grep -q "SENDGRID_API_KEY" .env.production; then
        success "SendGrid configurado"
    else
        warning "SendGrid no configurado"
    fi
    
    # Verificar Redis
    if grep -q "REDIS_URL" .env.production; then
        success "Redis configurado"
    else
        error "Redis no configurado"
    fi
}

validate_backup_strategy() {
    info "💾 Validando estrategia de backups..."
    
    if [ -f "scripts/backup_manager.sh" ]; then
        success "Script de backup disponible"
    else
        warning "Script de backup no encontrado"
    fi
    
    # Verificar que el script es ejecutable
    if [ -x "scripts/backup_manager.sh" ]; then
        success "Script de backup ejecutable"
    else
        warning "Script de backup no es ejecutable"
        chmod +x scripts/backup_manager.sh 2>/dev/null || true
    fi
}

validate_monitoring() {
    info "📊 Validando monitoreo..."
    
    # Verificar logging
    if [ -f "backend/logging_config_pro.py" ]; then
        success "Configuración de logging profesional disponible"
    else
        warning "Configuración de logging básica"
    fi
    
    # Verificar health check endpoint
    if grep -q "healthz" backend/urls.py; then
        success "Health check endpoint configurado"
    else
        warning "Health check endpoint no encontrado"
    fi
}

# ==========================================
# FUNCIÓN PRINCIPAL
# ==========================================

main() {
    print_banner
    
    # Ejecutar validaciones
    validate_environment
    validate_django_config
    validate_database
    validate_static_files
    validate_docker
    validate_security
    validate_external_services
    validate_backup_strategy
    validate_monitoring
    
    # Resumen final
    echo ""
    echo "=================================================="
    echo "📊 RESUMEN DE VALIDACIÓN"
    echo "=================================================="
    echo -e "${GREEN}✅ Pasadas: $PASSED${NC}"
    echo -e "${YELLOW}⚠️ Advertencias: $WARNINGS${NC}"
    echo -e "${RED}❌ Fallidas: $FAILED${NC}"
    echo "=================================================="
    
    # Decisión final
    if [ $FAILED -eq 0 ]; then
        if [ $WARNINGS -eq 0 ]; then
            echo -e "${GREEN}🚀 GO - LISTO PARA DESPLIEGUE${NC}"
            echo "   Todas las validaciones pasaron exitosamente"
        else
            echo -e "${YELLOW}🟡 GO CON PRECAUCIÓN${NC}"
            echo "   $WARNINGS advertencias encontradas"
            echo "   Revisar antes del despliegue"
        fi
        exit 0
    else
        echo -e "${RED}❌ NO-GO - DETENER DESPLIEGUE${NC}"
        echo "   $FAILED errores críticos encontrados"
        echo "   Corregir antes de continuar"
        exit 1
    fi
}

# Verificar que estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ Error: Ejecutar desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# Ejecutar validación
main "$@"