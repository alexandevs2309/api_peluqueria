#!/usr/bin/env python
"""
Script para ejecutar tests completos con coverage
"""
import os
import sys
import subprocess

def run_tests():
    """Ejecutar suite completa de tests"""
    print("[TESTS] Ejecutando tests con coverage...")
    
    # Comandos de testing
    commands = [
        # Tests unitarios con coverage
        ["python", "-m", "pytest", "--cov=apps", "--cov=backend", 
         "--cov-report=html", "--cov-report=term-missing", "-v"],
        
        # Tests de integración
        ["python", "-m", "pytest", "tests/integration/", "-v"],
        
        # Verificar configuración Django
        ["python", "manage.py", "check", "--deploy"],
        
        # Verificar migraciones
        ["python", "manage.py", "makemigrations", "--check", "--dry-run"],
    ]
    
    for cmd in commands:
        print(f"\n[RUN] Ejecutando: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[ERROR] Error en: {' '.join(cmd)}")
            print(result.stderr)
            return False
        else:
            print(f"[OK] Exitoso: {' '.join(cmd)}")
    
    print("\n[SUCCESS] Todos los tests pasaron!")
    print("[REPORT] Reporte de coverage disponible en: htmlcov/index.html")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)