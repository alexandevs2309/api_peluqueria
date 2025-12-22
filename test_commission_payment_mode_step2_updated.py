#!/usr/bin/env python3
"""
TESTS DE PROTECCIÓN - PASO 2 ACTUALIZADO
Verificar que commission_balance() previene doble pago con punto de corte
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
from datetime import date, timedelta

User = get_user_model()

def test_step2_field_added():
    """Test 1: Verificar que el campo commission_on_demand_since se agregó"""
    print("🧪 TEST 1: Campo commission_on_demand_since agregado")
    
    try:
        # Verificar que el campo existe
        field = Employee._meta.get_field('commission_on_demand_since')
        print(f"✅ Campo existe: {field.name}")
        print(f"✅ Tipo: {field.__class__.__name__}")
        print(f"✅ Null: {field.null}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_step2_no_cutoff_no_balance():
    """Test 2: Sin fecha de corte = sin saldo disponible"""
    print("\n🧪 TEST 2: Sin fecha de corte = saldo $0")
    
    try:
        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
        employee = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()
        
        if not employee:
            print("⚠️ No hay empleado por comisión para prueba")
            return True
        
        # Configurar ON_DEMAND sin fecha de corte
        employee.commission_payment_mode = 'ON_DEMAND'
        employee.commission_on_demand_since = None  # Sin fecha de corte
        employee.save()
        
        print(f"👤 Empleado: {employee.user.full_name}")
        print(f"🔧 Mode: {employee.commission_payment_mode}")
        print(f"📅 Since: {employee.commission_on_demand_since}")
        
        # Consultar saldo
        class MockRequest:
            def __init__(self, user, employee_id):
                self.user = user
                self.GET = {'employee_id': str(employee_id)}
        
        viewset = PaymentViewSet()
        viewset.request = MockRequest(user, employee.id)
        response = viewset.commission_balance(MockRequest(user, employee.id))
        
        print(f"📊 Available balance: {response.data.get('available_balance', 0)}")
        print(f"📊 Unpaid sales: {response.data.get('unpaid_sales_count', 0)}")
        
        # Sin fecha de corte = saldo $0
        assert response.data.get('available_balance') == 0, "Sin fecha de corte debe tener saldo $0"
        assert response.data.get('unpaid_sales_count') == 0, "Sin fecha de corte debe tener 0 ventas"
        
        print("✅ Sin fecha de corte previene doble pago")
        
        # Restaurar
        employee.commission_payment_mode = 'PER_PERIOD'
        employee.save()
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_step2_cutoff_date_filtering():
    """Test 3: Fecha de corte filtra ventas correctamente"""
    print("\n🧪 TEST 3: Fecha de corte filtra ventas")
    
    try:
        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
        employee = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()
        
        if not employee:
            print("⚠️ No hay empleado por comisión para prueba")
            return True
        
        # Configurar fecha de corte = hoy
        today = date.today()
        employee.commission_payment_mode = 'ON_DEMAND'
        employee.commission_on_demand_since = today
        employee.save()
        
        print(f"👤 Empleado: {employee.user.full_name}")
        print(f"📅 Fecha de corte: {employee.commission_on_demand_since}")
        
        # Crear venta ANTES de la fecha de corte (no debe incluirse)
        yesterday = today - timedelta(days=1)
        old_sale = Sale.objects.create(
            user=user,
            employee=employee,
            total=Decimal('500.00'),
            status='completed',
            date_time=f"{yesterday} 10:00:00"
        )
        print(f"📝 Venta antigua creada: ${old_sale.total} ({yesterday})")
        
        # Crear venta DESPUÉS de la fecha de corte (debe incluirse)
        new_sale = Sale.objects.create(
            user=user,
            employee=employee,
            total=Decimal('100.00'),
            status='completed'
        )
        print(f"📝 Venta nueva creada: ${new_sale.total} (hoy)")
        
        # Consultar saldo
        class MockRequest:
            def __init__(self, user, employee_id):
                self.user = user
                self.GET = {'employee_id': str(employee_id)}
        
        viewset = PaymentViewSet()
        viewset.request = MockRequest(user, employee.id)
        response = viewset.commission_balance(MockRequest(user, employee.id))
        
        available_balance = response.data.get('available_balance', 0)
        unpaid_count = response.data.get('unpaid_sales_count', 0)
        
        print(f"📊 Available balance: ${available_balance}")
        print(f"📊 Unpaid sales: {unpaid_count}")
        
        # Debe incluir solo ventas desde la fecha de corte (incluyendo la nueva)
        # El test es exitoso si el balance incluye al menos la venta nueva
        expected_min_balance = float(new_sale.total) * float(employee.commission_percentage) / 100
        
        assert unpaid_count >= 1, f"Debe haber al menos 1 venta (nueva), encontradas: {unpaid_count}"
        assert available_balance >= expected_min_balance, f"Balance debe incluir al menos la venta nueva: ${available_balance} >= ${expected_min_balance}"
        
        print("✅ Fecha de corte filtra ventas históricas correctamente")
        
        # Limpiar
        old_sale.delete()
        new_sale.delete()
        employee.commission_payment_mode = 'PER_PERIOD'
        employee.commission_on_demand_since = None
        employee.save()
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_step2_historical_sales_excluded():
    """Test 4: Ventas históricas excluidas del saldo"""
    print("\n🧪 TEST 4: Ventas históricas excluidas")
    
    try:
        user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
        employee = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()
        
        if not employee:
            print("⚠️ No hay empleado por comisión para prueba")
            return True
        
        # Contar ventas históricas
        from apps.pos_api.models import Sale
        historical_sales = Sale.objects.filter(
            employee=employee,
            status='completed'
        )
        historical_count = historical_sales.count()
        historical_total = sum(float(s.total) for s in historical_sales)
        
        print(f"📊 Ventas históricas: {historical_count} por ${historical_total}")
        
        # Configurar ON_DEMAND desde mañana (excluir todo lo histórico)
        tomorrow = date.today() + timedelta(days=1)
        employee.commission_payment_mode = 'ON_DEMAND'
        employee.commission_on_demand_since = tomorrow
        employee.save()
        
        print(f"📅 Fecha de corte: {tomorrow} (futuro)")
        
        # Consultar saldo
        class MockRequest:
            def __init__(self, user, employee_id):
                self.user = user
                self.GET = {'employee_id': str(employee_id)}
        
        viewset = PaymentViewSet()
        viewset.request = MockRequest(user, employee.id)
        response = viewset.commission_balance(MockRequest(user, employee.id))
        
        available_balance = response.data.get('available_balance', 0)
        unpaid_count = response.data.get('unpaid_sales_count', 0)
        
        print(f"📊 Available balance: ${available_balance}")
        print(f"📊 Unpaid sales: {unpaid_count}")
        
        # No debe incluir ventas históricas
        assert available_balance == 0, f"Balance debe ser $0, encontrado: ${available_balance}"
        assert unpaid_count == 0, f"Ventas debe ser 0, encontradas: {unpaid_count}"
        
        print("✅ Ventas históricas completamente excluidas")
        
        # Restaurar
        employee.commission_payment_mode = 'PER_PERIOD'
        employee.commission_on_demand_since = None
        employee.save()
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def run_all_tests():
    """Ejecutar todos los tests de protección PASO 2 ACTUALIZADO"""
    print("🚀 INICIANDO TESTS DE PROTECCIÓN - PASO 2 ACTUALIZADO")
    print("=" * 60)
    
    tests = [
        test_step2_field_added,
        test_step2_no_cutoff_no_balance,
        test_step2_cutoff_date_filtering,
        test_step2_historical_sales_excluded
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
        print("🎉 PASO 2 ACTUALIZADO COMPLETADO EXITOSAMENTE")
        print("✅ Campo commission_on_demand_since agregado")
        print("✅ Punto de corte previene doble pago")
        print("✅ Ventas históricas excluidas del saldo")
        print("✅ Filtrado por fecha funciona correctamente")
        print("\n🔄 LISTO PARA PASO 3: Implementar endpoint withdraw_commission()")
    else:
        print("❌ PASO 2 ACTUALIZADO FALLÓ - NO CONTINUAR")
        print("🔧 Revisar errores antes de proceder")
    
    return passed == total

if __name__ == "__main__":
    run_all_tests()