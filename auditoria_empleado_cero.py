#!/usr/bin/env python3
"""
AUDITORÍA ESPECÍFICA - EMPLEADO CON $0.00
Verificar por qué Yangelis Mejía tiene $0.00
"""
import os
import sys
import django

# Setup Django
sys.path.append('/home/alexander/Escritorio/clone/api_peluqueria-master')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee, Earning
from apps.payroll_api.models import PayrollSettlement

def auditar_empleado_cero():
    """Auditar específicamente empleados con $0.00"""
    print("🔍 AUDITORÍA ESPECÍFICA - EMPLEADOS CON $0.00")
    print("=" * 60)
    
    # Buscar settlements con $0.00
    settlements_cero = PayrollSettlement.objects.filter(
        gross_amount=0,
        status='OPEN'
    ).select_related('employee__user')
    
    print(f"📊 Settlements con $0.00 y estado OPEN: {settlements_cero.count()}")
    print()
    
    for settlement in settlements_cero:
        employee = settlement.employee
        print(f"👤 EMPLEADO: {employee.user.full_name or employee.user.email}")
        print(f"   Email: {employee.user.email}")
        print(f"   salary_type: {employee.salary_type}")
        print(f"   contractual_monthly_salary: ${employee.contractual_monthly_salary}")
        print(f"   commission_percentage: {employee.commission_percentage}%")
        print()
        
        # Verificar earnings
        earnings = Earning.objects.filter(employee=employee)
        print(f"💰 EARNINGS:")
        print(f"   Total earnings: {earnings.count()}")
        if earnings.exists():
            total = sum(e.amount for e in earnings)
            print(f"   Suma total: ${total}")
            print("   Últimos earnings:")
            for earning in earnings.order_by('-created_at')[:3]:
                print(f"     - ${earning.amount} | {earning.created_at.date()}")
        else:
            print("   ❌ NO hay earnings")
        print()
        
        # Análisis
        print("🔍 ANÁLISIS:")
        if employee.salary_type == 'fixed':
            if employee.contractual_monthly_salary > 0:
                print("   ❓ REVISAR: Empleado fixed con salario contractual pero sin lógica de sueldo fijo")
            else:
                print("   ✅ ESPERADO: Empleado fixed sin salario contractual = $0.00")
        elif employee.salary_type == 'commission':
            if not earnings.exists():
                print("   ✅ ESPERADO: Empleado commission sin earnings = $0.00")
            else:
                print("   ❓ REVISAR: Empleado commission con earnings pero settlement en $0.00")
        
        print("-" * 60)
        print()

if __name__ == "__main__":
    auditar_empleado_cero()