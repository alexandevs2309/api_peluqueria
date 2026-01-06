#!/usr/bin/env python3
"""
TEST DE CORRECCIÓN - BUG SUELDO FIJO
Verificar que la corrección funciona correctamente
"""
import os
import sys
import django

sys.path.append('/home/alexander/Escritorio/clone/api_peluqueria-master')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.payroll_api.models import PayrollSettlement
from apps.payroll_api.services import PayrollSettlementService
from decimal import Decimal

def test_bug_corregido():
    """Test para verificar que el bug del sueldo fijo está corregido"""
    print("🔧 TEST DE CORRECCIÓN - BUG SUELDO FIJO")
    print("=" * 60)
    
    # Buscar empleado fixed
    employee = Employee.objects.filter(salary_type='fixed').first()
    if not employee:
        print("❌ No hay empleados fixed para probar")
        return
    
    print(f"👤 Empleado: {employee.user.email}")
    print(f"   salary_type: {employee.salary_type}")
    print(f"   salary_amount (deprecated): ${employee.salary_amount}")
    print(f"   contractual_monthly_salary: ${employee.contractual_monthly_salary}")
    print()
    
    # Crear settlement de prueba
    settlement = PayrollSettlement.objects.filter(
        employee=employee,
        status='OPEN'
    ).first()
    
    if not settlement:
        print("❌ No hay settlement OPEN para probar")
        return
    
    print(f"📊 Settlement antes de corrección:")
    print(f"   ID: {settlement.id}")
    print(f"   fixed_salary_amount: ${settlement.fixed_salary_amount}")
    print(f"   gross_amount: ${settlement.gross_amount}")
    print()
    
    # Aplicar servicio corregido
    service = PayrollSettlementService()
    settlement_updated = service.calculate_settlement(settlement)
    
    print(f"📊 Settlement después de corrección:")
    print(f"   fixed_salary_amount: ${settlement_updated.fixed_salary_amount}")
    print(f"   gross_amount: ${settlement_updated.gross_amount}")
    print()
    
    # Verificar corrección
    expected_salary = employee.contractual_monthly_salary
    if settlement.frequency == 'biweekly':
        expected_salary = expected_salary / 2  # Quincenal
    
    print(f"🔍 VERIFICACIÓN:")
    print(f"   Salario esperado (quincenal): ${expected_salary}")
    print(f"   Salario calculado: ${settlement_updated.fixed_salary_amount}")
    
    if abs(settlement_updated.fixed_salary_amount - expected_salary) < Decimal('0.01'):
        print("   ✅ CORRECCIÓN EXITOSA")
    else:
        print("   ❌ CORRECCIÓN FALLIDA")
    
    print()
    print("✅ TEST COMPLETADO")

if __name__ == "__main__":
    test_bug_corregido()