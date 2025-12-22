#!/usr/bin/env python
"""
Script de prueba para el servicio de balance

Flujo de prueba:
1. ventas → earnings
2. preview → balance correcto  
3. pago → balance disminuye
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.services.balance import EmployeeBalanceService
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import Earning
from apps.employees_api.payroll_models import PayrollPayment
from apps.pos_api.models import Sale
from decimal import Decimal
from django.utils import timezone

def test_balance_service():
    print("=== PRUEBA DEL SERVICIO DE BALANCE ===\n")
    
    # Buscar un empleado existente
    try:
        employee = Employee.objects.filter(is_active=True).first()
        if not employee:
            print("❌ No hay empleados activos para probar")
            return
        
        print(f"👤 Empleado: {employee.user.email}")
        print(f"🏢 Tenant: {employee.tenant.name}")
        
        # 1. ESTADO INICIAL
        print("\n1️⃣ ESTADO INICIAL")
        initial_balance = EmployeeBalanceService.get_balance(employee.id)
        breakdown = EmployeeBalanceService.get_balance_breakdown(employee.id)
        
        print(f"Balance inicial: ${initial_balance}")
        print(f"Total earnings: ${breakdown['total_earnings']}")
        print(f"Total payments: ${breakdown['total_payments']}")
        
        # 2. CREAR EARNING SIMULADO
        print("\n2️⃣ CREAR EARNING SIMULADO")
        test_earning = Earning.objects.create(
            employee=employee,
            amount=Decimal('100.00'),
            earning_type='commission',
            description='Prueba balance service'
        )
        print(f"✅ Earning creado: ${test_earning.amount}")
        
        # 3. VERIFICAR BALANCE DESPUÉS DE EARNING
        print("\n3️⃣ BALANCE DESPUÉS DE EARNING")
        balance_after_earning = EmployeeBalanceService.get_balance(employee.id)
        expected_balance = initial_balance + Decimal('100.00')
        
        print(f"Balance esperado: ${expected_balance}")
        print(f"Balance calculado: ${balance_after_earning}")
        
        if balance_after_earning == expected_balance:
            print("✅ Balance correcto después de earning")
        else:
            print("❌ Balance incorrecto después de earning")
        
        # 4. CREAR PAGO SIMULADO
        print("\n4️⃣ CREAR PAGO SIMULADO")
        from apps.auth_api.models import User
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        
        test_payment = PayrollPayment.objects.create(
            employee=employee,
            tenant=employee.tenant,
            period_year=2024,
            period_index=1,
            period_frequency='biweekly',
            period_start_date=timezone.now().date(),
            period_end_date=timezone.now().date(),
            payment_type='commission',
            gross_amount=Decimal('50.00'),
            net_amount=Decimal('45.00'),  # Después de descuentos
            payment_method='cash',
            paid_by=admin_user
        )
        print(f"✅ Pago creado: ${test_payment.net_amount}")
        
        # 5. VERIFICAR BALANCE DESPUÉS DE PAGO
        print("\n5️⃣ BALANCE DESPUÉS DE PAGO")
        final_balance = EmployeeBalanceService.get_balance(employee.id)
        expected_final = balance_after_earning - Decimal('45.00')
        
        print(f"Balance esperado: ${expected_final}")
        print(f"Balance calculado: ${final_balance}")
        
        if final_balance == expected_final:
            print("✅ Balance correcto después de pago")
        else:
            print("❌ Balance incorrecto después de pago")
        
        # 6. BREAKDOWN FINAL
        print("\n6️⃣ BREAKDOWN FINAL")
        final_breakdown = EmployeeBalanceService.get_balance_breakdown(employee.id)
        print(f"Total earnings: ${final_breakdown['total_earnings']}")
        print(f"Total payments: ${final_breakdown['total_payments']}")
        print(f"Balance disponible: ${final_breakdown['available_balance']}")
        
        # 7. LIMPIAR DATOS DE PRUEBA
        print("\n7️⃣ LIMPIEZA")
        test_earning.delete()
        test_payment.delete()
        print("✅ Datos de prueba eliminados")
        
        print("\n🎉 PRUEBA COMPLETADA")
        
    except Exception as e:
        print(f"❌ Error en prueba: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_balance_service()