#!/usr/bin/env python
"""
Script de monitoreo para IntegrityError en refunds
Ejecutar: python monitor_refund_errors.py

Monitorea logs de Django para detectar intentos de doble refund
y genera reporte de incidencias.
"""

import re
import sys
from datetime import datetime, timedelta
from collections import defaultdict


def parse_log_file(log_path):
    """Parse log file buscando IntegrityError en refunds"""
    
    pattern = r'IntegrityError en refund de venta #(\d+): (.+)'
    errors = defaultdict(list)
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.search(pattern, line)
                if match:
                    sale_id = match.group(1)
                    error_msg = match.group(2)
                    timestamp = extract_timestamp(line)
                    
                    errors[sale_id].append({
                        'timestamp': timestamp,
                        'error': error_msg
                    })
    except FileNotFoundError:
        print(f"❌ Archivo de log no encontrado: {log_path}")
        return None
    
    return errors


def extract_timestamp(log_line):
    """Extraer timestamp de línea de log"""
    # Formato típico: [2024-01-15 10:30:45,123]
    match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', log_line)
    if match:
        return match.group(1)
    return 'Unknown'


def generate_report(errors):
    """Generar reporte de errores"""
    
    if not errors:
        print("✅ No se detectaron IntegrityError en refunds")
        return
    
    print(f"\n⚠️  REPORTE DE INTENTOS DE DOBLE REFUND")
    print(f"=" * 60)
    print(f"Total de ventas afectadas: {len(errors)}")
    print(f"Total de intentos duplicados: {sum(len(v) for v in errors.values())}")
    print(f"\nDetalle por venta:\n")
    
    for sale_id, incidents in sorted(errors.items()):
        print(f"  Venta #{sale_id}:")
        print(f"    Intentos: {len(incidents)}")
        for i, incident in enumerate(incidents, 1):
            print(f"      {i}. {incident['timestamp']} - {incident['error'][:80]}")
        print()
    
    print(f"=" * 60)
    print(f"\n💡 RECOMENDACIONES:")
    print(f"  - Revisar logs de aplicación para identificar origen de requests duplicados")
    print(f"  - Verificar si hay retry logic en frontend/API client")
    print(f"  - Considerar implementar idempotency keys si el problema persiste")


def main():
    """Main function"""
    
    # Configurar path del log (ajustar según tu setup)
    log_paths = [
        'logs/django.log',
        'logs/app.log',
        '/var/log/django/app.log',
    ]
    
    print("🔍 Monitoreando logs de refund...")
    
    errors = None
    for log_path in log_paths:
        errors = parse_log_file(log_path)
        if errors is not None:
            print(f"✅ Analizando: {log_path}")
            break
    
    if errors is None:
        print("\n❌ No se encontró ningún archivo de log válido")
        print(f"Paths intentados: {', '.join(log_paths)}")
        print("\nEjecuta con: python monitor_refund_errors.py <path_to_log>")
        sys.exit(1)
    
    generate_report(errors)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Path personalizado
        errors = parse_log_file(sys.argv[1])
        if errors:
            generate_report(errors)
    else:
        main()
