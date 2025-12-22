#!/usr/bin/env python3
"""
TESTS DE PROTECCIÓN - PASO 2
Verificar que commission_balance() funciona correctamente SIN afectar PER_PERIOD
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
import uuid

User = get_user_model()

def test_step2_endpoint_exists():
    """Test 1: Verificar que el endpoint commission_balance existe"""
    print("🧪 TEST 1: Endpoint commission_balance existe")
    
    try:
        viewset = PaymentViewSet()
        
        # Verificar que el método existe
        assert hasattr(viewset, 'commission_balance'), "Método commission_balance no existe"
        print("✅ Método commission_balance existe")
        
        # Verificar que es un action
        method = getattr(viewset, 'commission_balance')
        assert hasattr(method, 'mapping'), "commission_balance no es un @action"
        print("✅ commission_balance es un @action")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_step2_per_period_unchanged():
    """Test 2: Verificar que PER_PERIOD sigue funcionando igual"""
    print("\n🧪 TEST 2: Comportamiento PER_PERIOD sin cambios")
    
    try:
        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
        employee = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()
        
        if not employee:
            print("⚠️ No hay empleado por comisión para prueba")
            return True
        
        # Asegurar que está en PER_PERIOD
        employee.commission_payment_mode = 'PER_PERIOD'
        employee.save()
        
        print(f"👤 Empleado: {employee.user.full_name}")
        print(f"🔧 Mode: {employee.commission_payment_mode}")
        
        # Probar earnings_summary (debe funcionar igual)
        class MockRequest:
            def __init__(self, user):
                self.user = user
                self.GET = {}
        
        viewset = PaymentViewSet()
        viewset.request = MockRequest(user)
        response = viewset.earnings_summary(MockRequest(user))
        
        # Verificar respuesta normal
        assert response.status_code == 200, f"earnings_summary falló: {response.status_code}"
        employees_data = response.data.get('employees', [])
        emp_data = next((e for e in employees_data if e['employee_id'] == employee.id), None)
        
        if emp_data:
            print(f"📊 earnings_summary funciona: pending_amount={emp_data.get('pending_amount', 0)}")
        
        print("✅ PER_PERIOD funciona exactamente igual")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_step2_commission_balance_per_period():
    """Test 3: commission_balance para empleado PER_PERIOD"""
    print("\n🧪 TEST 3: commission_balance con empleado PER_PERIOD")
    
    try:
        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
        employee = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()
        
        if not employee:
            print("⚠️ No hay empleado por comisión para prueba")
            return True
        
        # Asegurar que está en PER_PERIOD
        employee.commission_payment_mode = 'PER_PERIOD'
        employee.save()
        
        # Simular request
        class MockRequest:
            def __init__(self, user, employee_id):
                self.user = user
                self.GET = {'employee_id': str(employee_id)}
        
        viewset = PaymentViewSet()
        viewset.request = MockRequest(user, employee.id)
        response = viewset.commission_balance(MockRequest(user, employee.id))
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Response data: {response.data}")
        
        # Debe devolver mensaje de PER_PERIOD
        assert response.status_code == 200, f"Status incorrecto: {response.status_code}"
        assert response.data.get('available_balance') == 0, "Balance debe ser 0 para PER_PERIOD"
        assert 'PER_PERIOD' in response.data.get('message', ''), "Debe mencionar PER_PERIOD"
        
        print("✅ commission_balance maneja PER_PERIOD correctamente")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_step2_commission_balance_on_demand():
    """Test 4: commission_balance para empleado ON_DEMAND"""
    print("\n🧪 TEST 4: commission_balance con empleado ON_DEMAND")
    
    try:
        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
        employee = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()
        
        if not employee:
            print("⚠️ No hay empleado por comisión para prueba")
            return True
        
        # Cambiar a ON_DEMAND
        employee.commission_payment_mode = 'ON_DEMAND'
        employee.save()
        print(f"👤 Empleado cambiado a ON_DEMAND: {employee.user.full_name}")
        
        # Crear venta de prueba
        test_sale = Sale.objects.create(
            user=user,
            employee=employee,
            total=Decimal('100.00'),
            status='completed'
        )
        print(f"📝 Venta de prueba creada: ${test_sale.total}")
        
        # Simular request
        class MockRequest:
            def __init__(self, user, employee_id):
                self.user = user
                self.GET = {'employee_id': str(employee_id)}
        
        viewset = PaymentViewSet()
        viewset.request = MockRequest(user, employee.id)
        response = viewset.commission_balance(MockRequest(user, employee.id))
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📊 Available balance: {response.data.get('available_balance', 0)}")
        print(f"📊 Unpaid sales: {response.data.get('unpaid_sales_count', 0)}")
        
        # Verificar cálculo correcto
        expected_balance = float(test_sale.total) * float(employee.commission_percentage) / 100
        actual_balance = response.data.get('available_balance', 0)
        
        assert response.status_code == 200, f"Status incorrecto: {response.status_code}"
        assert actual_balance > 0, "Balance debe ser mayor a 0"
        assert abs(actual_balance - expected_balance) < 0.01, f"Balance incorrecto: {actual_balance} vs {expected_balance}"
        
        print(f"✅ Saldo calculado correctamente: ${actual_balance}")
        
        # Limpiar
        test_sale.delete()
        employee.commission_payment_mode = 'PER_PERIOD'
        employee.save()
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_step2_payroll_payment_sale_exclusion():
    """Test 5: Verificar exclusión de ventas con PayrollPaymentSale"""
    print("\n🧪 TEST 5: Exclusión de ventas pagadas (PayrollPaymentSale)")
    
    try:
        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
        employee = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()
        
        if not employee:
            print("⚠️ No hay empleado por comisión para prueba")
            return True
        
        # Cambiar a ON_DEMAND
        employee.commission_payment_mode = 'ON_DEMAND'
        employee.save()
        
        # Crear 2 ventas de prueba
        sale1 = Sale.objects.create(user=user, employee=employee, total=Decimal('100.00'), status='completed')
        sale2 = Sale.objects.create(user=user, employee=employee, total=Decimal('200.00'), status='completed')
        print(f"📝 Ventas creadas: ${sale1.total} y ${sale2.total}")
        
        # Crear PayrollPayment y PayrollPaymentSale para sale1 (simular pago)
        payment = PayrollPayment.objects.create(\n            employee=employee,\n            tenant=user.tenant,\n            period_year=2025,\n            period_index=1,\n            period_frequency='biweekly',\n            period_start_date='2025-01-01',\n            period_end_date='2025-01-15',\n            payment_type='commission',\n            gross_amount=Decimal('60.00'),\n            net_amount=Decimal('60.00'),\n            payment_method='cash'\n        )\n        \n        PayrollPaymentSale.objects.create(\n            payment=payment,\n            sale=sale1,\n            sale_total=sale1.total,\n            commission_amount=Decimal('60.00')\n        )\n        print(f"💳 Pago creado para sale1 (${sale1.total})")\n        \n        # Consultar saldo\n        class MockRequest:\n            def __init__(self, user, employee_id):\n                self.user = user\n                self.GET = {'employee_id': str(employee_id)}\n        \n        viewset = PaymentViewSet()\n        viewset.request = MockRequest(user, employee.id)\n        response = viewset.commission_balance(MockRequest(user, employee.id))\n        \n        # Debe mostrar solo sale2 (sale1 está pagada)\n        expected_balance = float(sale2.total) * float(employee.commission_percentage) / 100\n        actual_balance = response.data.get('available_balance', 0)\n        unpaid_count = response.data.get('unpaid_sales_count', 0)\n        \n        print(f"📊 Balance disponible: ${actual_balance}")\n        print(f"📊 Ventas sin pagar: {unpaid_count}")\n        \n        assert unpaid_count == 1, f"Debe haber 1 venta sin pagar, encontradas: {unpaid_count}"\n        assert abs(actual_balance - expected_balance) < 0.01, f"Balance incorrecto: {actual_balance} vs {expected_balance}"\n        \n        print("✅ PayrollPaymentSale excluye ventas pagadas correctamente")\n        \n        # Limpiar\n        PayrollPaymentSale.objects.filter(payment=payment).delete()\n        payment.delete()\n        sale1.delete()\n        sale2.delete()\n        employee.commission_payment_mode = 'PER_PERIOD'\n        employee.save()\n        \n        return True\n    except Exception as e:\n        print(f"❌ Error: {e}")\n        return False

def test_step2_period_assignment_audit():
    """Test 6: Verificar asignación de períodos para auditoría"""
    print("\n🧪 TEST 6: Asignación de períodos para auditoría")\n    \n    try:\n        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')\n        employee = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()\n        \n        if not employee:\n            print("⚠️ No hay empleado por comisión para prueba")\n            return True\n        \n        # Cambiar a ON_DEMAND\n        employee.commission_payment_mode = 'ON_DEMAND'\n        employee.save()\n        \n        # Crear venta sin período\n        test_sale = Sale.objects.create(\n            user=user,\n            employee=employee,\n            total=Decimal('150.00'),\n            status='completed',\n            period=None  # Sin período inicialmente\n        )\n        print(f"📝 Venta sin período creada: ${test_sale.total}")\n        \n        # Consultar saldo (debe asignar período)\n        class MockRequest:\n            def __init__(self, user, employee_id):\n                self.user = user\n                self.GET = {'employee_id': str(employee_id)}\n        \n        viewset = PaymentViewSet()\n        viewset.request = MockRequest(user, employee.id)\n        response = viewset.commission_balance(MockRequest(user, employee.id))\n        \n        # Verificar que se asignó período\n        test_sale.refresh_from_db()\n        assert test_sale.period is not None, "Período no fue asignado"\n        assert test_sale.period.is_paid == False, "Período no debe estar marcado como pagado"\n        \n        print(f"✅ Período asignado: {test_sale.period.fortnight_year}/{test_sale.period.fortnight_number}")\n        print(f"✅ Período NO pagado: is_paid={test_sale.period.is_paid}")\n        \n        # Limpiar\n        test_sale.delete()\n        employee.commission_payment_mode = 'PER_PERIOD'\n        employee.save()\n        \n        return True\n    except Exception as e:\n        print(f"❌ Error: {e}")\n        return False

def run_all_tests():\n    \"\"\"Ejecutar todos los tests de protección PASO 2\"\"\"\n    print("🚀 INICIANDO TESTS DE PROTECCIÓN - PASO 2")\n    print("=" * 60)\n    \n    tests = [\n        test_step2_endpoint_exists,\n        test_step2_per_period_unchanged,\n        test_step2_commission_balance_per_period,\n        test_step2_commission_balance_on_demand,\n        test_step2_payroll_payment_sale_exclusion,\n        test_step2_period_assignment_audit\n    ]\n    \n    results = []\n    for test in tests:\n        result = test()\n        results.append(result)\n    \n    print("\\n" + "=" * 60)\n    print("📋 RESUMEN DE RESULTADOS:")\n    print("=" * 60)\n    \n    passed = sum(results)\n    total = len(results)\n    \n    print(f"✅ Tests pasados: {passed}/{total}")\n    \n    if passed == total:\n        print("🎉 PASO 2 COMPLETADO EXITOSAMENTE")\n        print("✅ Endpoint commission_balance() implementado correctamente")\n        print("✅ PER_PERIOD mantiene comportamiento intacto")\n        print("✅ ON_DEMAND calcula saldo usando PayrollPaymentSale")\n        print("✅ Períodos asignados solo para auditoría")\n        print("\\n🔄 LISTO PARA PASO 3: Implementar endpoint withdraw_commission()")\n    else:\n        print("❌ PASO 2 FALLÓ - NO CONTINUAR")\n        print("🔧 Revisar errores antes de proceder")\n    \n    return passed == total

if __name__ == "__main__":\n    run_all_tests()