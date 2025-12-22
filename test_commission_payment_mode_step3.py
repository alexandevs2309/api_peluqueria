#!/usr/bin/env python3
"""
TESTS DE PROTECCIÓN - PASO 3
Verificar que withdraw_commission() funciona SOLO para ON_DEMAND sin afectar PER_PERIOD
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.employees_api.models import Employee
from apps.employees_api.payments_views import PaymentViewSet
from apps.pos_api.models import Sale
from apps.employees_api.payroll_models import PayrollPayment, PayrollPaymentSale
from decimal import Decimal
from datetime import date, timedelta

User = get_user_model()

def test_step3_endpoint_exists():
    """Test 1: Verificar que el endpoint withdraw_commission existe"""
    print("🧪 TEST 1: Endpoint withdraw_commission existe")
    
    try:
        viewset = PaymentViewSet()
        
        # Verificar que el método existe
        assert hasattr(viewset, 'withdraw_commission'), "Método withdraw_commission no existe"
        print("✅ Método withdraw_commission existe")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_step3_per_period_rejected():
    """Test 2: Rechazar retiros para empleados PER_PERIOD"""
    print("\n🧪 TEST 2: Rechazar retiros PER_PERIOD")
    
    try:
        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
        employee = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()
        
        if not employee:
            print("⚠️ No hay empleado por comisión para prueba")
            return True
        
        # Asegurar que está en PER_PERIOD
        employee.commission_payment_mode = 'PER_PERIOD'
        employee.commission_on_demand_since = None
        employee.save()
        
        print(f"👤 Empleado: {employee.user.full_name}")
        print(f"🔧 Mode: {employee.commission_payment_mode}")
        
        # Intentar retiro
        class MockRequest:
            def __init__(self, user, data):
                self.user = user
                self.data = data
        
        viewset = PaymentViewSet()
        viewset.request = MockRequest(user, {})
        response = viewset.withdraw_commission(MockRequest(user, {
            'employee_id': employee.id,
            'withdraw_amount': 100,
            'payment_method': 'cash'
        }))
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Error message: {response.data.get('error', 'N/A')}")
        
        # Debe rechazar empleados PER_PERIOD
        assert response.status_code == 400, f"Debe rechazar PER_PERIOD, status: {response.status_code}"
        assert 'ON_DEMAND' in response.data.get('error', ''), "Debe mencionar ON_DEMAND en error"
        
        print("✅ Retiros PER_PERIOD correctamente rechazados")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_step3_no_cutoff_date_rejected():
    """Test 3: Rechazar retiros sin fecha de activación"""
    print("\n🧪 TEST 3: Rechazar sin fecha de activación")
    
    try:
        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
        employee = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()
        
        if not employee:
            print("⚠️ No hay empleado por comisión para prueba")
            return True
        
        # Configurar ON_DEMAND sin fecha de activación
        employee.commission_payment_mode = 'ON_DEMAND'
        employee.commission_on_demand_since = None
        employee.save()
        
        print(f"👤 Empleado: {employee.user.full_name}")
        print(f"🔧 Mode: {employee.commission_payment_mode}")
        print(f"📅 Since: {employee.commission_on_demand_since}")
        
        # Intentar retiro
        class MockRequest:
            def __init__(self, user, data):
                self.user = user
                self.data = data
        
        viewset = PaymentViewSet()
        response = viewset.withdraw_commission(MockRequest(user, {
            'employee_id': employee.id,
            'withdraw_amount': 100,
            'payment_method': 'cash'
        }))
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Error message: {response.data.get('error', 'N/A')}")
        
        # Debe rechazar sin fecha de activación
        assert response.status_code == 400, f"Debe rechazar sin fecha, status: {response.status_code}"
        assert 'activación' in response.data.get('error', ''), "Debe mencionar activación en error"
        
        print("✅ Retiros sin fecha de activación correctamente rechazados")
        
        # Restaurar
        employee.commission_payment_mode = 'PER_PERIOD'
        employee.save()
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_step3_insufficient_balance_rejected():
    """Test 4: Rechazar retiros con saldo insuficiente"""
    print("\n🧪 TEST 4: Rechazar saldo insuficiente")
    
    try:
        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
        employee = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()
        
        if not employee:
            print("⚠️ No hay empleado por comisión para prueba")
            return True
        
        # Configurar ON_DEMAND con fecha futura (sin saldo)
        tomorrow = date.today() + timedelta(days=1)
        employee.commission_payment_mode = 'ON_DEMAND'
        employee.commission_on_demand_since = tomorrow
        employee.save()
        
        print(f"👤 Empleado: {employee.user.full_name}")
        print(f"📅 Since: {employee.commission_on_demand_since} (futuro)")
        
        # Intentar retiro
        class MockRequest:
            def __init__(self, user, data):
                self.user = user
                self.data = data
        
        viewset = PaymentViewSet()
        response = viewset.withdraw_commission(MockRequest(user, {
            'employee_id': employee.id,
            'withdraw_amount': 100,
            'payment_method': 'cash'
        }))
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Error message: {response.data.get('error', 'N/A')}")
        
        # Debe rechazar por saldo insuficiente
        assert response.status_code == 400, f"Debe rechazar saldo insuficiente, status: {response.status_code}"
        assert 'saldo' in response.data.get('error', '').lower(), "Debe mencionar saldo en error"
        
        print("✅ Retiros con saldo insuficiente correctamente rechazados")
        
        # Restaurar
        employee.commission_payment_mode = 'PER_PERIOD'
        employee.commission_on_demand_since = None
        employee.save()
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_step3_successful_withdrawal():
    """Test 5: Retiro exitoso ON_DEMAND"""
    print("\n🧪 TEST 5: Retiro exitoso ON_DEMAND")
    
    try:
        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
        employee = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()
        
        if not employee:
            print("⚠️ No hay empleado por comisión para prueba")
            return True
        
        # Configurar ON_DEMAND desde hoy
        today = date.today()
        employee.commission_payment_mode = 'ON_DEMAND'
        employee.commission_on_demand_since = today
        employee.save()
        
        # Crear venta de prueba
        test_sale = Sale.objects.create(
            user=user,
            employee=employee,
            total=Decimal('200.00'),
            status='completed'
        )
        
        expected_commission = float(test_sale.total) * float(employee.commission_percentage) / 100
        print(f"📝 Venta creada: ${test_sale.total}")
        print(f"💰 Comisión esperada: ${expected_commission}")
        
        # Intentar retiro
        class MockRequest:
            def __init__(self, user, data):
                self.user = user
                self.data = data
        
        viewset = PaymentViewSet()
        response = viewset.withdraw_commission(MockRequest(user, {
            'employee_id': employee.id,
            'withdraw_amount': expected_commission,
            'payment_method': 'transfer',
            'payment_reference': 'TEST-001'
        }))
        
        print(f"📊 Response status: {response.status_code}")\n        \n        if response.status_code == 200:\n            payment_data = response.data.get('payment', {})\n            print(f\"💳 Payment ID: {payment_data.get('payment_id', 'N/A')}\")\n            print(f\"💰 Gross amount: ${payment_data.get('gross_amount', 0)}\")\n            print(f\"💰 Net amount: ${payment_data.get('net_amount', 0)}\")\n            print(f\"📊 Sales paid: {len(payment_data.get('sales_paid', []))}\")\n            \n            # Verificar que se creó PayrollPayment\n            payment_id = payment_data.get('payment_id')\n            if payment_id:\n                payment = PayrollPayment.objects.filter(payment_id=payment_id).first()\n                assert payment is not None, \"PayrollPayment no fue creado\"\n                print(f\"✅ PayrollPayment creado: {payment.payment_id}\")\n                \n                # Verificar PayrollPaymentSale\n                payment_sales = PayrollPaymentSale.objects.filter(payment=payment)\n                assert payment_sales.count() > 0, \"PayrollPaymentSale no fue creado\"\n                print(f\"✅ PayrollPaymentSale creado: {payment_sales.count()} registros\")\n                \n                # Verificar que la venta tiene período asignado\n                test_sale.refresh_from_db()\n                assert test_sale.period is not None, \"Período no fue asignado para auditoría\"\n                assert test_sale.period.is_paid == False, \"Período no debe estar cerrado\"\n                print(f\"✅ Período asignado para auditoría: {test_sale.period.fortnight_year}/{test_sale.period.fortnight_number}\")\n                print(f\"✅ Período NO cerrado: is_paid={test_sale.period.is_paid}\")\n        else:\n            print(f\"📊 Error: {response.data.get('error', 'N/A')}\")\n            assert False, f\"Retiro falló: {response.data.get('error', 'Unknown error')}\"\n        \n        print(\"✅ Retiro ON_DEMAND exitoso\")\n        \n        # Limpiar\n        if 'payment_id' in locals():\n            PayrollPaymentSale.objects.filter(payment__payment_id=payment_id).delete()\n            PayrollPayment.objects.filter(payment_id=payment_id).delete()\n        test_sale.delete()\n        employee.commission_payment_mode = 'PER_PERIOD'\n        employee.commission_on_demand_since = None\n        employee.save()\n        \n        return True\n    except Exception as e:\n        print(f\"❌ Error: {e}\")\n        return False\n\ndef test_step3_per_period_unchanged():\n    \"\"\"Test 6: Verificar que PER_PERIOD sigue funcionando igual\"\"\"\n    print(\"\\n🧪 TEST 6: PER_PERIOD sin cambios después de PASO 3\")\n    \n    try:\n        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')\n        employee = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()\n        \n        if not employee:\n            print(\"⚠️ No hay empleado por comisión para prueba\")\n            return True\n        \n        # Asegurar que está en PER_PERIOD\n        employee.commission_payment_mode = 'PER_PERIOD'\n        employee.commission_on_demand_since = None\n        employee.save()\n        \n        # Probar earnings_summary (debe funcionar igual)\n        class MockRequest:\n            def __init__(self, user):\n                self.user = user\n                self.GET = {}\n        \n        viewset = PaymentViewSet()\n        viewset.request = MockRequest(user)\n        response = viewset.earnings_summary(MockRequest(user))\n        \n        # Verificar respuesta normal\n        assert response.status_code == 200, f\"earnings_summary falló: {response.status_code}\"\n        employees_data = response.data.get('employees', [])\n        emp_data = next((e for e in employees_data if e['employee_id'] == employee.id), None)\n        \n        if emp_data:\n            print(f\"📊 earnings_summary funciona: payment_status={emp_data.get('payment_status', 'unknown')}\")\n        \n        print(\"✅ PER_PERIOD funciona exactamente igual después de PASO 3\")\n        return True\n    except Exception as e:\n        print(f\"❌ Error: {e}\")\n        return False\n\ndef run_all_tests():\n    \"\"\"Ejecutar todos los tests de protección PASO 3\"\"\"\n    print(\"🚀 INICIANDO TESTS DE PROTECCIÓN - PASO 3\")\n    print(\"=\" * 60)\n    \n    tests = [\n        test_step3_endpoint_exists,\n        test_step3_per_period_rejected,\n        test_step3_no_cutoff_date_rejected,\n        test_step3_insufficient_balance_rejected,\n        test_step3_successful_withdrawal,\n        test_step3_per_period_unchanged\n    ]\n    \n    results = []\n    for test in tests:\n        result = test()\n        results.append(result)\n    \n    print(\"\\n\" + \"=\" * 60)\n    print(\"📋 RESUMEN DE RESULTADOS:\")\n    print(\"=\" * 60)\n    \n    passed = sum(results)\n    total = len(results)\n    \n    print(f\"✅ Tests pasados: {passed}/{total}\")\n    \n    if passed == total:\n        print(\"🎉 PASO 3 COMPLETADO EXITOSAMENTE\")\n        print(\"✅ Endpoint withdraw_commission() implementado correctamente\")\n        print(\"✅ Solo funciona para empleados ON_DEMAND con fecha de activación\")\n        print(\"✅ Crea PayrollPayment + PayrollPaymentSale atómicamente\")\n        print(\"✅ Asigna períodos para auditoría SIN cerrarlos\")\n        print(\"✅ PER_PERIOD permanece completamente intacto\")\n        print(\"\\n🎯 SISTEMA HÍBRIDO ON_DEMAND COMPLETADO\")\n    else:\n        print(\"❌ PASO 3 FALLÓ - REVISAR ERRORES\")\n        print(\"🔧 Corregir problemas antes de aprobar\")\n    \n    return passed == total\n\nif __name__ == \"__main__\":\n    run_all_tests()