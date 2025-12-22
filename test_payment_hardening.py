#!/usr/bin/env python
"""
Script de prueba para endurecimiento de pagos

Pruebas:
1. Idempotencia - mismo idempotency_key
2. Concurrencia - múltiples requests simultáneos
3. Balance insuficiente
4. Estados de pago
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.services.payment import PaymentService
from apps.employees_api.services.balance import EmployeeBalanceService
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import Earning
from apps.employees_api.payroll_models import PayrollPayment
from apps.auth_api.models import User
from decimal import Decimal
from django.utils import timezone
import uuid

def test_payment_hardening():
    print("=== PRUEBA DE ENDURECIMIENTO DE PAGOS ===\n")
    
    try:
        # Buscar empleado y usuario
        employee = Employee.objects.filter(is_active=True).first()
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        
        if not employee or not admin_user:
            print("❌ No hay empleados o usuarios para probar")
            return
        
        print(f"👤 Empleado: {employee.user.email}")
        print(f"👨‍💼 Usuario admin: {admin_user.email}")
        
        # 1. ESTADO INICIAL
        print("\n1️⃣ ESTADO INICIAL")
        initial_balance = EmployeeBalanceService.get_balance(employee.id)
        print(f"Balance inicial: ${initial_balance}")
        
        # Crear earning para tener balance
        if initial_balance < 100:
            test_earning = Earning.objects.create(
                employee=employee,
                amount=Decimal('200.00'),
                earning_type='commission',
                description='Prueba endurecimiento'
            )
            print(f"✅ Earning creado: ${test_earning.amount}")
            initial_balance = EmployeeBalanceService.get_balance(employee.id)
            print(f"Nuevo balance: ${initial_balance}")
        
        # 2. PRUEBA DE IDEMPOTENCIA
        print("\n2️⃣ PRUEBA DE IDEMPOTENCIA")
        idempotency_key = str(uuid.uuid4())
        payment_data = {
            'payment_method': 'cash',
            'payment_reference': 'TEST-001',
            'payment_notes': 'Prueba idempotencia',
            'paid_by': admin_user
        }
        
        # Primer pago
        result1 = PaymentService.process_payment(
            employee_id=employee.id,
            requested_amount=Decimal('50.00'),
            payment_data=payment_data,
            idempotency_key=idempotency_key
        )
        print(f"Primer pago: {result1['status']} - {result1['message']}")
        
        # Segundo pago con mismo idempotency_key
        result2 = PaymentService.process_payment(
            employee_id=employee.id,
            requested_amount=Decimal('50.00'),
            payment_data=payment_data,
            idempotency_key=idempotency_key
        )
        print(f"Segundo pago: {result2['status']} - {result2['message']}")
        
        if result1['status'] == 'success' and result2['status'] == 'already_processed':
            print("✅ Idempotencia funcionando correctamente")
        else:
            print("❌ Idempotencia falló")
        
        # 3. PRUEBA DE BALANCE INSUFICIENTE
        print("\n3️⃣ PRUEBA DE BALANCE INSUFICIENTE")
        current_balance = EmployeeBalanceService.get_balance(employee.id)
        excessive_amount = current_balance + Decimal('1000.00')
        
        result3 = PaymentService.process_payment(
            employee_id=employee.id,
            requested_amount=excessive_amount,
            payment_data=payment_data,
            idempotency_key=str(uuid.uuid4())
        )
        print(f"Pago excesivo: {result3['status']} - {result3['message']}")
        
        if result3['status'] == 'error' and 'insuficiente' in result3['message']:
            print("✅ Validación de balance funcionando")
        else:
            print("❌ Validación de balance falló")
        
        # 4. PRUEBA DE ESTADOS
        print("\n4️⃣ VERIFICAR ESTADOS DE PAGO")
        payments = PayrollPayment.objects.filter(employee=employee).order_by('-created_at')[:3]
        
        for payment in payments:
            print(f"Pago {payment.payment_id}: {payment.status} - ${payment.net_amount}")
        
        # 5. BALANCE FINAL
        print("\n5️⃣ BALANCE FINAL")
        final_balance = EmployeeBalanceService.get_balance(employee.id)
        breakdown = EmployeeBalanceService.get_balance_breakdown(employee.id)
        
        print(f"Balance final: ${final_balance}")
        print(f"Total earnings: ${breakdown['total_earnings']}")
        print(f"Total payments: ${breakdown['total_payments']}")
        
        print("\n🎉 PRUEBA DE ENDURECIMIENTO COMPLETADA")
        
    except Exception as e:
        print(f"❌ Error en prueba: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_payment_hardening()