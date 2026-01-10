#!/usr/bin/env python
"""
Validador de variables de entorno para producción
Ejecutar antes del despliegue
"""
import os
import sys
import re
from urllib.parse import urlparse

class ProductionEnvValidator:
    """Validador de variables de entorno para producción"""
    
    REQUIRED_VARS = [
        'SECRET_KEY',
        'DEBUG',
        'ALLOWED_HOSTS',
        'CSRF_TRUSTED_ORIGINS',
        'DATABASE_URL',
        'REDIS_URL',
        'CELERY_BROKER_URL',
        'CELERY_RESULT_BACKEND',
        'CORS_ALLOWED_ORIGINS',
        'SENTRY_DSN',
        'SENDGRID_API_KEY',
        'SENDGRID_FROM_EMAIL',
    ]
    
    FORBIDDEN_VALUES = {
        'DEBUG': ['True', 'true', '1'],
        'SECRET_KEY': ['your-secret-key-here', 'django-insecure-'],
        'ALLOWED_HOSTS': ['*'],
        'CORS_ALLOWED_ORIGINS': ['*'],
    }
    
    def __init__(self, env_file='.env'):
        self.env_file = env_file
        self.errors = []
        self.warnings = []
        self._load_env()
    
    def _load_env(self):
        """Cargar variables de entorno desde archivo"""
        if os.path.exists(self.env_file):
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key, value)
    
    def validate_all(self):
        """Ejecutar todas las validaciones"""
        self.validate_required_vars()
        self.validate_forbidden_values()
        self.validate_secret_key()
        self.validate_database_url()
        self.validate_redis_url()
        self.validate_sentry_dsn()
        self.validate_sendgrid()
        self.validate_cors_origins()
        self.validate_allowed_hosts()
        
        return len(self.errors) == 0
    
    def validate_required_vars(self):
        """Validar variables requeridas"""
        for var in self.REQUIRED_VARS:
            if not os.getenv(var):
                self.errors.append(f"❌ Variable requerida faltante: {var}")
    
    def validate_forbidden_values(self):
        """Validar valores prohibidos"""
        for var, forbidden in self.FORBIDDEN_VALUES.items():
            value = os.getenv(var, '')
            if value in forbidden:
                self.errors.append(f"❌ Valor prohibido en {var}: {value}")
    
    def validate_secret_key(self):
        """Validar SECRET_KEY"""
        secret_key = os.getenv('SECRET_KEY', '')
        
        if len(secret_key) < 50:
            self.errors.append("❌ SECRET_KEY debe tener al menos 50 caracteres")
        
        if 'django-insecure-' in secret_key:
            self.errors.append("❌ SECRET_KEY no debe contener 'django-insecure-'")
        
        if secret_key == 'your-secret-key-here':
            self.errors.append("❌ SECRET_KEY debe ser cambiado del valor por defecto")
    
    def validate_database_url(self):
        """Validar DATABASE_URL"""
        db_url = os.getenv('DATABASE_URL', '')
        
        if not db_url.startswith('postgres'):
            self.errors.append("❌ DATABASE_URL debe usar PostgreSQL (postgres://)")
        
        try:
            parsed = urlparse(db_url)
            if not parsed.hostname:
                self.errors.append("❌ DATABASE_URL: hostname faltante")
            if not parsed.username:
                self.errors.append("❌ DATABASE_URL: usuario faltante")
            if not parsed.password:
                self.errors.append("❌ DATABASE_URL: password faltante")
            if not parsed.path or parsed.path == '/':
                self.errors.append("❌ DATABASE_URL: nombre de base de datos faltante")
        except Exception as e:
            self.errors.append(f"❌ DATABASE_URL inválido: {e}")
    
    def validate_redis_url(self):
        """Validar REDIS_URL"""
        redis_url = os.getenv('REDIS_URL', '')
        
        if not redis_url.startswith('redis://'):
            self.errors.append("❌ REDIS_URL debe comenzar con redis://")
        
        # Validar que Celery URLs sean consistentes
        celery_broker = os.getenv('CELERY_BROKER_URL', '')
        celery_result = os.getenv('CELERY_RESULT_BACKEND', '')
        
        if not celery_broker.startswith('redis://'):
            self.errors.append("❌ CELERY_BROKER_URL debe usar Redis")
        
        if not celery_result.startswith('redis://'):
            self.errors.append("❌ CELERY_RESULT_BACKEND debe usar Redis")
    
    def validate_sentry_dsn(self):
        """Validar Sentry DSN"""
        sentry_dsn = os.getenv('SENTRY_DSN', '')
        
        if not sentry_dsn.startswith('https://'):
            self.errors.append("❌ SENTRY_DSN debe comenzar con https://")
        
        if 'sentry.io' not in sentry_dsn:
            self.warnings.append("⚠️ SENTRY_DSN no parece ser de sentry.io")
        
        # Validar environment
        sentry_env = os.getenv('SENTRY_ENVIRONMENT', '')
        if sentry_env not in ['production', 'staging']:
            self.warnings.append("⚠️ SENTRY_ENVIRONMENT debería ser 'production' o 'staging'")
    
    def validate_sendgrid(self):
        """Validar configuración SendGrid"""
        api_key = os.getenv('SENDGRID_API_KEY', '')
        from_email = os.getenv('SENDGRID_FROM_EMAIL', '')
        
        if not api_key.startswith('SG.'):
            self.errors.append("❌ SENDGRID_API_KEY debe comenzar con 'SG.'")
        
        if not from_email or '@' not in from_email:
            self.errors.append("❌ SENDGRID_FROM_EMAIL debe ser un email válido")
        
        if 'gmail.com' in from_email or 'example.com' in from_email:
            self.warnings.append("⚠️ SENDGRID_FROM_EMAIL debería usar tu dominio")
    
    def validate_cors_origins(self):
        """Validar CORS origins"""
        cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
        
        if not cors_origins:
            self.errors.append("❌ CORS_ALLOWED_ORIGINS no puede estar vacío")
            return
        
        origins = [origin.strip() for origin in cors_origins.split(',')]
        
        for origin in origins:
            if not origin.startswith('https://'):
                self.errors.append(f"❌ CORS origin debe usar HTTPS: {origin}")
            
            if 'localhost' in origin:
                self.errors.append(f"❌ localhost no debe estar en CORS origins: {origin}")
    
    def validate_allowed_hosts(self):
        """Validar ALLOWED_HOSTS"""
        allowed_hosts = os.getenv('ALLOWED_HOSTS', '')
        
        if not allowed_hosts:
            self.errors.append("❌ ALLOWED_HOSTS no puede estar vacío")
            return
        
        hosts = [host.strip() for host in allowed_hosts.split(',')]
        
        if '*' in hosts:
            self.errors.append("❌ ALLOWED_HOSTS no debe contener '*' en producción")
        
        if 'testserver' in hosts:
            self.errors.append("❌ 'testserver' no debe estar en ALLOWED_HOSTS")
        
        for host in hosts:
            if host in ['127.0.0.1', 'localhost'] and len(hosts) == 1:
                self.warnings.append("⚠️ Solo localhost en ALLOWED_HOSTS, ¿es correcto?")
    
    def print_results(self):
        """Imprimir resultados de validación"""
        print("=" * 60)
        print("🔍 VALIDACIÓN DE VARIABLES DE ENTORNO - PRODUCCIÓN")
        print("=" * 60)
        
        if self.errors:
            print("\n❌ ERRORES CRÍTICOS:")
            for error in self.errors:
                print(f"  {error}")
        
        if self.warnings:
            print("\n⚠️ ADVERTENCIAS:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ Todas las validaciones pasaron correctamente")
        elif not self.errors:
            print(f"\n✅ Sin errores críticos ({len(self.warnings)} advertencias)")
        else:
            print(f"\n❌ {len(self.errors)} errores críticos encontrados")
        
        print("=" * 60)
        
        return len(self.errors) == 0

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validar variables de entorno para producción')
    parser.add_argument('--env-file', default='.env', help='Archivo de variables de entorno')
    
    args = parser.parse_args()
    
    validator = ProductionEnvValidator(args.env_file)
    is_valid = validator.validate_all()
    validator.print_results()
    
    if not is_valid:
        print("\n🚨 DESPLIEGUE BLOQUEADO: Corregir errores antes de continuar")
        sys.exit(1)
    else:
        print("\n🚀 Variables de entorno válidas para producción")
        sys.exit(0)

if __name__ == '__main__':
    main()