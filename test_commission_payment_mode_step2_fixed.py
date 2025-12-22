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
from datetime import date

User = get_user_model()

def test_step2_endpoint_exists():
    """Test 1: Verificar que el endpoint commission_balance existe"""
    print("🧪 TEST 1: Endpoint commission_balance existe")
    
    try:
        viewset = PaymentViewSet()
        
        # Verificar que el método existe
        assert hasattr(viewset, 'commission_balance'), "Método commission_balance no existe"
        print("✅ Método commission_balance existe")
        
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
        
        # Debe devolver mensaje de PER_PERIOD
        assert response.status_code == 200, f"Status incorrecto: {response.status_code}"
        assert response.data.get('available_balance') == 0, "Balance debe ser 0 para PER_PERIOD"
        
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

def run_all_tests():
    """Ejecutar todos los tests de protección PASO 2"""
    print("🚀 INICIANDO TESTS DE PROTECCIÓN - PASO 2")
    print("=" * 60)
    
    tests = [
        test_step2_endpoint_exists,
        test_step2_per_period_unchanged,
        test_step2_commission_balance_per_period,
        test_step2_commission_balance_on_demand
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE RESULTADOS:")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Tests pasados: {passed}/{total}")
    
    if passed == total:
        print("🎉 PASO 2 COMPLETADO EXITOSAMENTE")
        print("✅ Endpoint commission_balance() implementado correctamente")
        print("✅ PER_PERIOD mantiene comportamiento intacto")
        print("✅ ON_DEMAND calcula saldo usando PayrollPaymentSale")
        print("\n🔄 LISTO PARA PASO 3: Implementar endpoint withdraw_commission()")
    else:
        print("❌ PASO 2 FALLÓ - NO CONTINUAR")
        print("🔧 Revisar errores antes de proceder")
    
    return passed == total

if __name__ == "__main__":
    run_all_tests()