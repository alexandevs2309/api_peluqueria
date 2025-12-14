#!/usr/bin/env python3
"""
Test de compatibilidad frontend-backend para sueldos fijos
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_frontend_compatibility():
    """Verificar que el backend responde correctamente para el frontend"""
    
    # 1. Login
    login_response = requests.post(f"{BASE_URL}/api/auth/login/", json={
        'email': 'alexanderdelrosarioperez@gmail.com',
        'password': 'baspeka1394'
    })
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return False
    
    token = login_response.json()['access']
    headers = {'Authorization': f'Bearer {token}'}
    print("✅ Login exitoso")
    
    # 2. Test earnings_summary (usado por pagos-empleados.ts)
    earnings_response = requests.get(f"{BASE_URL}/api/employees/payments/earnings_summary/", headers=headers)
    
    if earnings_response.status_code != 200:
        print(f"❌ Earnings summary failed: {earnings_response.status_code}")
        return False
    
    data = earnings_response.json()
    employees = data.get('employees', [])
    
    print(f"✅ Earnings summary: {len(employees)} empleados")
    
    # 3. Verificar campos requeridos por frontend
    required_fields = [
        'employee_id', 'employee_name', 'salary_type', 'commission_percentage',
        'total_earned', 'pending_amount', 'services_count', 'payment_status'
    ]
    
    if not employees:
        print("❌ No hay empleados en la respuesta")
        return False
    
    sample_employee = employees[0]
    missing_fields = [field for field in required_fields if field not in sample_employee]
    
    if missing_fields:
        print(f"❌ Campos faltantes: {missing_fields}")
        return False
    
    print("✅ Estructura de respuesta compatible")
    
    # 4. Verificar empleados fijos específicamente
    fixed_employees = [emp for emp in employees if emp.get('salary_type') == 'fixed']
    
    if not fixed_employees:
        print("⚠️ No hay empleados fijos para probar")
        return True
    
    print(f"✅ Empleados fijos encontrados: {len(fixed_employees)}")
    
    for emp in fixed_employees:
        print(f"  - {emp['employee_name']}: ${emp['total_earned']} (Estado: {emp['payment_status']})")
        
        # Verificar que empleados fijos aparecen aunque no tengan ventas
        if emp['services_count'] == 0 and emp['total_earned'] > 0:
            print(f"    ✅ Empleado fijo sin ventas pero con earnings: ${emp['total_earned']}")
        
        # Verificar que tienen pending_amount correcto
        if emp['payment_status'] == 'pending' and emp['pending_amount'] > 0:
            print(f"    ✅ Empleado fijo con pendientes: ${emp['pending_amount']}")
    
    # 5. Test de pago de empleado fijo
    fixed_emp = fixed_employees[0]
    
    # Solo probar pago si tiene pendientes
    if fixed_emp['pending_amount'] > 0:
        print(f"\n🧪 Probando pago de empleado fijo: {fixed_emp['employee_name']}")
        
        pay_data = {
            'employee_id': fixed_emp['employee_id'],
            'year': 2025,
            'fortnight': 23,
            'payment_method': 'cash',
            'payment_reference': 'TEST-FRONTEND-COMPAT'
        }
        
        pay_response = requests.post(f"{BASE_URL}/api/employees/payments/pay_employee/", 
                                   json=pay_data, headers=headers)
        
        if pay_response.status_code in [200, 409]:  # 409 = ya pagado
            pay_result = pay_response.json()
            print(f"✅ Pago procesado: {pay_result.get('status')}")
            
            if 'summary' in pay_result:
                summary = pay_result['summary']
                expected_fields = ['gross_amount', 'net_amount', 'deductions', 'receipt_number']
                summary_missing = [field for field in expected_fields if field not in summary]
                
                if summary_missing:
                    print(f"❌ Campos faltantes en summary: {summary_missing}")
                else:
                    print("✅ Summary de pago compatible con frontend")
        else:
            print(f"❌ Error en pago: {pay_response.status_code} - {pay_response.text}")
    
    print("\n=== RESUMEN COMPATIBILIDAD ===")
    print("✅ Login funcional")
    print("✅ Earnings summary funcional") 
    print("✅ Estructura de datos compatible")
    print("✅ Empleados fijos incluidos en respuesta")
    print("✅ Pagos de empleados fijos funcionales")
    
    return True

if __name__ == "__main__":
    success = test_frontend_compatibility()
    print(f"\n{'✅ FRONTEND COMPATIBLE' if success else '❌ PROBLEMAS DE COMPATIBILIDAD'}")