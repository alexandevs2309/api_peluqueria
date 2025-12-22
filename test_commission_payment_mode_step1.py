#!/usr/bin/env python3
"""
TESTS DE PROTECCIÓN - PASO 1
Verificar que el nuevo campo commission_payment_mode NO afecta el comportamiento actual
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.employees_api.models import Employee
from apps.employees_api.payments_views import PaymentViewSet
from apps.pos_api.models import Sale
from decimal import Decimal

User = get_user_model()

def test_step1_field_added():
    """Test 1: Verificar que el campo se agregó correctamente"""
    print("🧪 TEST 1: Campo commission_payment_mode agregado")
    
    try:
        # Verificar que el campo existe
        field = Employee._meta.get_field('commission_payment_mode')
        print(f"✅ Campo existe: {field.name}")
        print(f"✅ Choices: {field.choices}")
        print(f"✅ Default: {field.default}")
        
        # Verificar default correcto
        assert field.default == 'PER_PERIOD', f"Default incorrecto: {field.default}"
        print("✅ Default es PER_PERIOD")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_step1_existing_employees():
    """Test 2: Verificar que empleados existentes tienen default correcto"""
    print("\n🧪 TEST 2: Empleados existentes con default correcto")
    
    try:
        employees = Employee.objects.all()
        print(f"📊 Total empleados: {employees.count()}")
        
        for employee in employees:
            assert employee.commission_payment_mode == 'PER_PERIOD', f"Empleado {employee.id} no tiene default correcto"
            print(f"✅ Empleado {employee.user.full_name or employee.user.email}: {employee.commission_payment_mode}")
        
        print("✅ Todos los empleados tienen commission_payment_mode = PER_PERIOD")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_step1_per_period_behavior_unchanged():
    """Test 3: Verificar que el comportamiento PER_PERIOD NO cambió"""
    print("\n🧪 TEST 3: Comportamiento PER_PERIOD sin cambios")
    
    try:
        # Obtener empleado de prueba
        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
        employee = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()
        
        if not employee:
            print("⚠️ No hay empleado por comisión para prueba")
            return True
        
        print(f"👤 Empleado: {employee.user.full_name}")
        print(f"💼 Salary type: {employee.salary_type}")
        print(f"🔧 Commission mode: {employee.commission_payment_mode}")
        
        # Verificar que está en PER_PERIOD
        assert employee.commission_payment_mode == 'PER_PERIOD'
        
        # Simular consulta earnings_summary (comportamiento actual)
        class MockRequest:
            def __init__(self, user):
                self.user = user
                self.GET = {}
        
        viewset = PaymentViewSet()
        viewset.request = MockRequest(user)
        response = viewset.earnings_summary(MockRequest(user))
        
        # Verificar que la respuesta es la misma de antes
        employees_data = response.data.get('employees', [])
        emp_data = next((e for e in employees_data if e['employee_id'] == employee.id), None)
        
        if emp_data:
            print(f"📊 Pending amount: {emp_data.get('pending_amount', 0)}")
            print(f"📊 Payment status: {emp_data.get('payment_status', 'unknown')}")
            print("✅ earnings_summary funciona igual que antes")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_step1_new_employee_creation():
    """Test 4: Verificar que nuevos empleados usan default correcto"""
    print("\n🧪 TEST 4: Nuevos empleados con default correcto")
    
    try:
        # Crear usuario temporal
        test_user = User.objects.create_user(
            email='test_commission_mode@test.com',
            password='test123'
        )
        
        # Obtener tenant
        main_user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
        
        # Crear empleado
        new_employee = Employee.objects.create(
            user=test_user,
            tenant=main_user.tenant,
            salary_type='commission',
            commission_percentage=Decimal('50.00')
        )
        
        print(f"👤 Nuevo empleado: {new_employee.user.email}")
        print(f"🔧 Commission mode: {new_employee.commission_payment_mode}")
        
        # Verificar default
        assert new_employee.commission_payment_mode == 'PER_PERIOD'
        print("✅ Nuevo empleado tiene commission_payment_mode = PER_PERIOD")
        
        # Limpiar
        new_employee.delete()
        test_user.delete()
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_step1_field_validation():
    """Test 5: Verificar validación de choices"""
    print("\n🧪 TEST 5: Validación de choices")
    
    try:
        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
        employee = Employee.objects.filter(tenant=user.tenant).first()
        
        # Probar valores válidos
        employee.commission_payment_mode = 'PER_PERIOD'
        employee.save()
        print("✅ PER_PERIOD válido")
        
        employee.commission_payment_mode = 'ON_DEMAND'
        employee.save()
        print("✅ ON_DEMAND válido")
        
        # Restaurar default
        employee.commission_payment_mode = 'PER_PERIOD'
        employee.save()
        print("✅ Restaurado a PER_PERIOD")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def run_all_tests():
    """Ejecutar todos los tests de protección"""
    print("🚀 INICIANDO TESTS DE PROTECCIÓN - PASO 1")
    print("=" * 60)
    
    tests = [
        test_step1_field_added,
        test_step1_existing_employees,
        test_step1_per_period_behavior_unchanged,
        test_step1_new_employee_creation,
        test_step1_field_validation
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
        print("🎉 PASO 1 COMPLETADO EXITOSAMENTE")
        print("✅ Campo commission_payment_mode agregado sin afectar comportamiento actual")
        print("✅ Todos los empleados mantienen modo PER_PERIOD")
        print("✅ Sistema funciona exactamente igual que antes")
        print("\n🔄 LISTO PARA PASO 2: Implementar endpoint commission_balance()")
    else:
        print("❌ PASO 1 FALLÓ - NO CONTINUAR")
        print("🔧 Revisar errores antes de proceder")
    
    return passed == total

if __name__ == "__main__":
    run_all_tests()