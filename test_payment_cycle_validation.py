#!/usr/bin/env python3
"""
Test de validación de ciclo de pago
Verifica que can_pay y pay_block_reason funcionen correctamente
"""
import os
import sys
import django
from datetime import date, timedelta
from django.utils import timezone

# Setup Django
sys.path.append('/home/alexander/Escritorio/clone/api_peluqueria-master')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.payroll_api.models import PayrollSettlement
from apps.employees_api.models import Employee
from apps.tenants_api.models import Tenant

def test_payment_cycle_validation():
    """Test de validación de ciclo de pago"""
    print("🧪 INICIANDO TEST DE VALIDACIÓN DE CICLO DE PAGO")
    print("=" * 60)
    
    # Obtener tenant y empleado de prueba
    tenant = Tenant.objects.first()
    if not tenant:
        print("❌ No hay tenants disponibles")
        return
    
    employee = Employee.objects.filter(tenant=tenant, is_active=True).first()
    if not employee:
        print("❌ No hay empleados disponibles")
        return
    
    print(f"📋 Tenant: {tenant.name}")
    print(f"👤 Empleado: {employee.user.email}")
    print(f"💰 Tipo salario: {employee.salary_type}")
    print()
    
    # Test 1: Settlement con período futuro (no se puede pagar)
    print("🔍 TEST 1: Período futuro")
    today = timezone.now().date()
    future_settlement = PayrollSettlement.objects.create(
        employee=employee,
        tenant=tenant,
        frequency='biweekly',
        period_start=today + timedelta(days=1),
        period_end=today + timedelta(days=15),
        period_year=today.year,
        period_index=1,
        status='READY',
        gross_amount=1000.00,
        net_amount=800.00
    )
    
    print(f"   Período: {future_settlement.period_start} - {future_settlement.period_end}")
    print(f"   can_pay: {future_settlement.can_pay}")
    print(f"   pay_block_reason: {future_settlement.pay_block_reason}")
    print()
    
    # Test 2: Settlement con período actual (se puede pagar)
    print("🔍 TEST 2: Período actual")
    current_settlement = PayrollSettlement.objects.create(
        employee=employee,
        tenant=tenant,
        frequency='biweekly',
        period_start=today - timedelta(days=15),
        period_end=today,
        period_year=today.year,
        period_index=2,
        status='READY',
        gross_amount=1000.00,
        net_amount=800.00
    )
    
    print(f"   Período: {current_settlement.period_start} - {current_settlement.period_end}")
    print(f"   can_pay: {current_settlement.can_pay}")
    print(f"   pay_block_reason: {current_settlement.pay_block_reason}")
    print()
    
    # Test 3: Settlement semanal (viernes)
    print("🔍 TEST 3: Frecuencia semanal")
    weekly_settlement = PayrollSettlement.objects.create(
        employee=employee,
        tenant=tenant,
        frequency='weekly',
        period_start=today - timedelta(days=7),
        period_end=today,
        period_year=today.year,
        period_index=3,
        status='READY',
        gross_amount=500.00,
        net_amount=400.00
    )
    
    print(f"   Hoy es: {today.strftime('%A')} ({today})")
    print(f"   can_pay: {weekly_settlement.can_pay}")
    print(f"   pay_block_reason: {weekly_settlement.pay_block_reason}")
    print()
    
    # Test 4: Settlement mensual
    print("🔍 TEST 4: Frecuencia mensual")
    monthly_settlement = PayrollSettlement.objects.create(
        employee=employee,
        tenant=tenant,
        frequency='monthly',
        period_start=today.replace(day=1),
        period_end=today,
        period_year=today.year,
        period_index=4,
        status='READY',
        gross_amount=2000.00,
        net_amount=1600.00
    )
    
    print(f"   Día del mes: {today.day}")
    print(f"   can_pay: {monthly_settlement.can_pay}")
    print(f"   pay_block_reason: {monthly_settlement.pay_block_reason}")
    print()
    
    # Limpiar datos de prueba
    print("🧹 Limpiando datos de prueba...")
    PayrollSettlement.objects.filter(
        id__in=[future_settlement.id, current_settlement.id, 
                weekly_settlement.id, monthly_settlement.id]
    ).delete()
    
    print("✅ TEST COMPLETADO")

if __name__ == "__main__":
    test_payment_cycle_validation()