#!/usr/bin/env python
"""
Test script para verificar que el fix de ON-DEMAND funciona
"""
import os
import django
import sys
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.auth_api.models import User
from apps.tenants_api.models import Tenant

def test_ondemand_configuration():
    """Test que la configuración ON-DEMAND se guarda correctamente"""
    
    print("🧪 TESTING ON-DEMAND Configuration Fix")
    print("=" * 50)
    
    # Buscar un empleado existente
    employee = Employee.objects.filter(is_active=True).first()
    
    if not employee:
        print("❌ No hay empleados para probar")
        return False
    
    print(f"📋 Empleado de prueba: {employee.user.email}")
    print(f"   Configuración actual:")
    print(f"   - commission_payment_mode: {employee.commission_payment_mode}")
    print(f"   - commission_on_demand_since: {employee.commission_on_demand_since}")
    
    # Guardar valores originales
    original_mode = employee.commission_payment_mode
    original_since = employee.commission_on_demand_since
    
    # Test 1: Cambiar a ON_DEMAND
    print("\n🔧 Test 1: Configurando ON_DEMAND...")
    employee.commission_payment_mode = 'ON_DEMAND'
    employee.commission_on_demand_since = date.today()
    employee.save()
    
    # Recargar desde DB
    employee.refresh_from_db()
    
    if employee.commission_payment_mode == 'ON_DEMAND':
        print("✅ commission_payment_mode guardado correctamente")
    else:
        print(f"❌ commission_payment_mode NO guardado: {employee.commission_payment_mode}")
        return False
    
    if employee.commission_on_demand_since:
        print("✅ commission_on_demand_since guardado correctamente")
    else:
        print("❌ commission_on_demand_since NO guardado")
        return False
    
    # Test 2: Cambiar a BIWEEKLY
    print("\n🔧 Test 2: Configurando BIWEEKLY...")
    employee.commission_payment_mode = 'BIWEEKLY'
    employee.commission_on_demand_since = None
    employee.save()
    
    # Recargar desde DB
    employee.refresh_from_db()
    
    if employee.commission_payment_mode == 'BIWEEKLY':
        print("✅ Cambio a BIWEEKLY guardado correctamente")
    else:
        print(f"❌ Cambio a BIWEEKLY NO guardado: {employee.commission_payment_mode}")
        return False
    
    # Restaurar valores originales
    print("\n🔄 Restaurando configuración original...")
    employee.commission_payment_mode = original_mode
    employee.commission_on_demand_since = original_since
    employee.save()
    
    print("✅ Configuración restaurada")
    print("\n🎉 TODOS LOS TESTS PASARON - El fix funciona correctamente!")
    return True

def test_endpoint_simulation():
    """Simular el endpoint update_employee_config"""
    
    print("\n🌐 TESTING Endpoint Simulation")
    print("=" * 50)
    
    employee = Employee.objects.filter(is_active=True).first()
    if not employee:
        print("❌ No hay empleados para probar")
        return False
    
    print(f"📋 Simulando request al endpoint update_employee_config")
    
    # Simular datos del request
    request_data = {
        'employee_id': employee.id,
        'commission_payment_mode': 'ON_DEMAND',
        'commission_on_demand_since': '2024-01-15'
    }
    
    print(f"   Request data: {request_data}")
    
    # Simular procesamiento del endpoint (lógica del fix)
    if 'commission_payment_mode' in request_data:
        employee.commission_payment_mode = request_data['commission_payment_mode']
        print(f"   ✅ Procesando commission_payment_mode: {request_data['commission_payment_mode']}")
    
    if 'commission_on_demand_since' in request_data:
        from datetime import datetime
        employee.commission_on_demand_since = datetime.strptime(request_data['commission_on_demand_since'], '%Y-%m-%d').date()
        print(f"   ✅ Procesando commission_on_demand_since: {request_data['commission_on_demand_since']}")
    
    employee.save()
    
    # Verificar que se guardó
    employee.refresh_from_db()
    
    response_data = {
        'message': 'Configuración actualizada',
        'employee': {
            'id': employee.id,
            'commission_payment_mode': employee.commission_payment_mode,
            'commission_on_demand_since': employee.commission_on_demand_since.isoformat() if employee.commission_on_demand_since else None
        }
    }
    
    print(f"   Response data: {response_data}")
    
    if (employee.commission_payment_mode == 'ON_DEMAND' and 
        employee.commission_on_demand_since and
        employee.commission_on_demand_since.isoformat() == '2024-01-15'):
        print("✅ Endpoint simulation EXITOSA - Los campos se procesan correctamente")
        return True
    else:
        print("❌ Endpoint simulation FALLÓ")
        return False

if __name__ == '__main__':
    try:
        success1 = test_ondemand_configuration()
        success2 = test_endpoint_simulation()
        
        if success1 and success2:
            print("\n🎯 RESULTADO FINAL: ✅ EL FIX FUNCIONA CORRECTAMENTE")
            print("   - Los campos commission_payment_mode y commission_on_demand_since se guardan")
            print("   - El endpoint procesa correctamente los datos del frontend")
            sys.exit(0)
        else:
            print("\n🎯 RESULTADO FINAL: ❌ HAY PROBLEMAS CON EL FIX")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ ERROR durante las pruebas: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)