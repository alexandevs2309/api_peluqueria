#!/usr/bin/env python
"""
Script para migrar al nuevo sistema de pagos optimizado
Ejecutar: python migrate_payments_system.py
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import transaction
from apps.employees_api.models import Employee
from decimal import Decimal

def migrate_employee_fields():
    """Migrar campos deprecated a nuevos campos"""
    print("🔄 Migrando campos de empleados...")
    
    with transaction.atomic():
        employees = Employee.objects.all()
        migrated = 0
        
        for emp in employees:
            # Migrar salary_amount a contractual_monthly_salary si está vacío
            if emp.contractual_monthly_salary == 0 and emp.salary_amount > 0:
                # salary_amount era quincenal, convertir a mensual
                emp.contractual_monthly_salary = emp.salary_amount * 2
                emp.save()
                migrated += 1
                print(f"  ✅ {emp.user.email}: ${emp.salary_amount} quincenal → ${emp.contractual_monthly_salary} mensual")
        
        print(f"✅ Migrados {migrated} empleados")

def cleanup_redundant_files():
    """Mover archivos redundantes a backup"""
    print("🧹 Limpiando archivos redundantes...")
    
    base_path = Path(__file__).parent / "apps" / "employees_api"
    backup_path = base_path / "backup_old_system"
    backup_path.mkdir(exist_ok=True)
    
    files_to_backup = [
        "earnings_views.py",
        "earnings_views_fixed.py", 
        "pending_payments_views.py"
    ]
    
    for filename in files_to_backup:
        source = base_path / filename
        if source.exists():
            target = backup_path / filename
            source.rename(target)
            print(f"  📦 {filename} → backup/")
    
    print("✅ Archivos movidos a backup/")

def verify_system():
    """Verificar que el nuevo sistema funciona"""
    print("🔍 Verificando nuevo sistema...")
    
    try:
        from apps.employees_api.payments_views import PaymentViewSet
        from apps.employees_api.models import Employee
        
        # Verificar que los modelos funcionan
        employee_count = Employee.objects.count()
        print(f"  ✅ {employee_count} empleados en sistema")
        
        # Verificar que PaymentViewSet se importa correctamente
        viewset = PaymentViewSet()
        print(f"  ✅ PaymentViewSet cargado correctamente")
        
        print("✅ Sistema verificado")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    return True

def main():
    print("🚀 Iniciando migración del sistema de pagos...")
    print("=" * 50)
    
    try:
        # 1. Migrar campos
        migrate_employee_fields()
        print()
        
        # 2. Verificar sistema
        if verify_system():
            print()
            
            # 3. Limpiar archivos (solo si verificación pasa)
            cleanup_redundant_files()
            print()
            
            print("🎉 ¡Migración completada exitosamente!")
            print("\n📋 Resumen de cambios:")
            print("  • Sistema unificado en payments_views.py")
            print("  • URLs simplificadas")
            print("  • Campos deprecated migrados")
            print("  • Archivos redundantes en backup/")
            print("\n🔗 Nuevos endpoints:")
            print("  • POST /api/employees/payments/pay_employee/")
            print("  • GET  /api/employees/payments/pending_payments/")
            print("  • GET  /api/employees/payments/earnings_summary/")
            print("  • GET  /api/employees/{id}/pending-sales/")
            
        else:
            print("❌ Migración cancelada por errores en verificación")
            
    except Exception as e:
        print(f"❌ Error durante migración: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()