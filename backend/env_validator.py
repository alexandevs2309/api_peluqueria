"""
Validador de variables de entorno - backend/env_validator.py
"""
import os
import sys
from urllib.parse import urlparse

# VARIABLES OBLIGATORIAS EN PRODUCCIÓN
REQUIRED_PROD_VARS = {
    'SECRET_KEY': {
        'min_length': 50,
        'description': 'Django secret key'
    },
    'DATABASE_URL': {
        'format': 'postgresql://',
        'description': 'PostgreSQL connection string'
    },
    'REDIS_URL': {
        'format': 'redis://',
        'description': 'Redis connection string'
    },
    'CELERY_BROKER_URL': {
        'format': 'redis://',
        'description': 'Celery broker URL'
    },
    'SENTRY_DSN': {
        'format': 'https://',
        'description': 'Sentry error tracking'
    },
    'SENDGRID_API_KEY': {
        'format': 'SG.',
        'description': 'SendGrid email API key'
    },
    'ALLOWED_HOSTS': {
        'description': 'Comma-separated allowed hosts'
    },
    'CSRF_TRUSTED_ORIGINS': {
        'description': 'Comma-separated trusted origins'
    }
}

# VARIABLES PROHIBIDAS EN PRODUCCIÓN
FORBIDDEN_PROD_VARS = [
    'DEBUG=True',
    'CELERY_TASK_ALWAYS_EAGER=True',
    'DISABLE_SENTRY=True'
]

def validate_production_env():
    """Validar variables de entorno para producción."""
    errors = []
    warnings = []
    
    # Verificar variables obligatorias
    for var_name, config in REQUIRED_PROD_VARS.items():
        value = os.getenv(var_name)
        
        if not value:
            errors.append(f"❌ {var_name}: FALTANTE - {config['description']}")
            continue
            
        # Validar formato
        if 'format' in config and not value.startswith(config['format']):
            errors.append(f"❌ {var_name}: Formato inválido, debe empezar con '{config['format']}'")
            
        # Validar longitud mínima
        if 'min_length' in config and len(value) < config['min_length']:
            errors.append(f"❌ {var_name}: Muy corto, mínimo {config['min_length']} caracteres")
    
    # Verificar variables prohibidas
    for forbidden in FORBIDDEN_PROD_VARS:
        var_name, bad_value = forbidden.split('=')
        if os.getenv(var_name) == bad_value:
            errors.append(f"❌ {var_name}: Valor prohibido en producción ({bad_value})")
    
    # Validaciones específicas
    _validate_database_url(errors)
    _validate_allowed_hosts(errors, warnings)
    
    return errors, warnings

def _validate_database_url(errors):
    """Validar DATABASE_URL específicamente."""
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        parsed = urlparse(db_url)
        if parsed.scheme != 'postgresql':
            errors.append("❌ DATABASE_URL: Debe usar PostgreSQL")
        if not parsed.hostname:
            errors.append("❌ DATABASE_URL: Hostname faltante")

def _validate_allowed_hosts(errors, warnings):
    """Validar ALLOWED_HOSTS."""
    allowed_hosts = os.getenv('ALLOWED_HOSTS', '')
    if 'localhost' in allowed_hosts or '127.0.0.1' in allowed_hosts:
        warnings.append("⚠️ ALLOWED_HOSTS: Contiene hosts de desarrollo")

def check_env_or_exit():
    """Validar entorno y salir si hay errores críticos."""
    if os.getenv('DJANGO_SETTINGS_MODULE', '').endswith('_prod'):
        errors, warnings = validate_production_env()
        
        if warnings:
            print("ADVERTENCIAS:")
            for warning in warnings:
                print(f"  {warning}")
        
        if errors:
            print("ERRORES CRÍTICOS:")
            for error in errors:
                print(f"  {error}")
            print("\n❌ NO SE PUEDE INICIAR EN PRODUCCIÓN")
            sys.exit(1)
        
        print("✅ Validación de entorno: APROBADA")

if __name__ == '__main__':
    check_env_or_exit()