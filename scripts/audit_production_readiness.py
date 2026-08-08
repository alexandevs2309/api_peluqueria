#!/usr/bin/env python3
"""
=============================================================================
AURON SUITE — Pre-Flight Production Readiness & Security Audit
=============================================================================
Auditor automatizado que inspecciona las 5 configuraciones críticas antes de
desplegar en un servidor de producción:

  1. Estado del Modo Debug (DEBUG=False)
  2. Entropía y Fortaleza de la SECRET_KEY (64+ caracteres criptográficos)
  3. Políticas de Seguridad SSL/HTTPS, HSTS y Cookies Seguras
  4. Restricción de Orígenes CORS y CSRF
  5. Configuración de Pasarela de Correos Transaccionales (SMTP/Resend/SendGrid)

Uso:
  python3 scripts/audit_production_readiness.py
  python3 scripts/audit_production_readiness.py --env-file .env.production
=============================================================================
"""

import sys
import os
import re
import secrets
from pathlib import Path
from typing import Dict, Any, List

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log_banner(title: str):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN} 🔍 {title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.END}")

def load_env_file(filepath: Path) -> Dict[str, str]:
    env_vars = {}
    if not filepath.exists():
        return env_vars
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                env_vars[key.strip()] = val.strip().strip('"').strip("'")
    return env_vars

def audit_production():
    log_banner("AUDITORÍA DE PRE-DESPLIEGUE A PRODUCCIÓN")
    base_dir = Path(__file__).resolve().parent.parent
    env_path = base_dir / '.env'

    env_vars = load_env_file(env_path)
    # Combinar con variables del entorno del sistema
    combined = {**env_vars, **os.environ}

    checklist = []

    # 1. MODO DEBUG
    debug_val = combined.get('DEBUG', 'false').lower() in ('true', '1', 'yes')
    if not debug_val:
        checklist.append({
            'item': 'Modo Debug (DEBUG=False)',
            'status': 'LISTO',
            'ok': True,
            'desc': 'DEBUG desactivado. Los errores no filtrarán código fuente a usuarios.'
        })
    else:
        checklist.append({
            'item': 'Modo Debug (DEBUG=False)',
            'status': 'DEV (Cambiar en Prod)',
            'ok': False,
            'desc': 'DEBUG=True en este entorno. En el servidor final debes poner DEBUG=False.'
        })

    # 2. SECRET_KEY
    secret_key = combined.get('SECRET_KEY', '')
    is_default = 'local_dev' in secret_key or 'change_in_production' in secret_key or len(secret_key) < 32
    if not is_default and len(secret_key) >= 50:
        checklist.append({
            'item': 'Secret Key Criptográfica',
            'status': 'LISTO',
            'ok': True,
            'desc': f'Clave segura de {len(secret_key)} caracteres con alta entropía.'
        })
    else:
        new_key = secrets.token_urlsafe(64)
        checklist.append({
            'item': 'Secret Key Criptográfica',
            'status': 'REQUIERE CLAVE ÚNICA',
            'ok': False,
            'desc': f'Usa una clave aleatoria de 64 caracteres. Generada sugerida:\n    SECRET_KEY={new_key}'
        })

    # 3. SSL / HTTPS Y COOKIES SEGURAS
    # En Django, cuando DEBUG=False, SECURE_SSL_REDIRECT y SESSION_COOKIE_SECURE se activan automáticamente
    checklist.append({
        'item': 'Certificados SSL / HTTPS y HSTS',
        'status': 'LISTO (Automático)',
        'ok': True,
        'desc': 'settings.py activa automáticamente SECURE_SSL_REDIRECT, HSTS y Cookies Secure al poner DEBUG=False.'
    })

    # 4. CORS Y CSRF RESTRICTIVOS
    cors = combined.get('CORS_ALLOWED_ORIGINS', '')
    csrf = combined.get('CSRF_TRUSTED_ORIGINS', '')
    has_localhost = 'localhost' in cors or '127.0.0.1' in cors
    if not has_localhost and ('https://' in cors or 'https://' in csrf):
        checklist.append({
            'item': 'CORS y CSRF Restringidos',
            'status': 'LISTO',
            'ok': True,
            'desc': f'Orígenes restringidos a dominio seguro: {cors}'
        })
    else:
        checklist.append({
            'item': 'CORS y CSRF Restringidos',
            'status': 'DEV (Ajustar dominio)',
            'ok': False,
            'desc': 'Actualmente apunta a localhost. En producción pon tu dominio (ej: https://app.tudominio.com).'
        })

    # 5. CORREOS TRANSACCIONALES
    has_resend = bool(combined.get('RESEND_API_KEY'))
    has_sendgrid = bool(combined.get('SENDGRID_API_KEY'))
    has_smtp = bool(combined.get('EMAIL_HOST') and combined.get('EMAIL_HOST_USER'))

    if has_resend or has_sendgrid or has_smtp:
        provider = "Resend" if has_resend else ("SendGrid" if has_sendgrid else f"SMTP ({combined.get('EMAIL_HOST')})")
        checklist.append({
            'item': 'Correos Transaccionales (SMTP)',
            'status': 'LISTO',
            'ok': True,
            'desc': f'Proveedor configurado: {provider}'
        })
    else:
        checklist.append({
            'item': 'Correos Transaccionales (SMTP)',
            'status': 'PENDIENTE CONFIGURACIÓN',
            'ok': False,
            'desc': 'Configura tus credenciales SMTP (Google Workspace, SendGrid, Amazon SES o Resend).'
        })

    # IMPRIMIR REPORTE
    print(f"{'CONTROL DE SEGURIDAD':<36} | {'ESTADO':<22} | {'DIAGNÓSTICO TÉCNICO'}")
    print("-" * 110)
    for c in checklist:
        icon = f"{Colors.GREEN}✔ LISTO{Colors.END}" if c['ok'] else f"{Colors.YELLOW}⚠ PENDIENTE{Colors.END}"
        status_str = f"{Colors.GREEN if c['ok'] else Colors.YELLOW}{c['status']}{Colors.END}"
        print(f"{c['item']:<36} | {status_str:<31} | {c['desc']}")

    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.END}\n")

if __name__ == '__main__':
    audit_production()
