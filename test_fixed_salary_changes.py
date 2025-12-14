#!/usr/bin/env python3
"""
Test para validar cambios en manejo de sueldos fijos
"""
import os
import sys
import django
import requests
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.append('/app')
django.setup()

from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import FortnightSummary
from apps.auth_api.models import User
from apps.tenants_api.models import Tenant

BASE_URL = "http://localhost:8000"
TEST_CREDENTIALS = {
    'email': 'alexanderdelrosarioperez@gmail.com',
    'password': 'baspeka1394'
}

def get_auth_token():
    """Obtener token de autenticación"""
    response = requests.post(f"{BASE_URL}/auth/login/", json=TEST_CREDENTIALS)
    if response.status_code == 200:
        return response.json().get('access_token')
    raise Exception(f"Login failed: {response.text}")

def test_fixed_salary_logic():
    """Test de lógica de sueldos fijos"""
    print("=== TEST: Lógica de Sueldos Fijos ===")
    
    try:
        # Buscar empleados con sueldo fijo
        tenant = Tenant.objects.get(name="alexander barber")
        employees = Employee.objects.filter(
            tenant=tenant,
            salary_type='fixed',
            is_active=True
        )
        
        print(f"Empleados con sueldo fijo encontrados: {employees.count()}")
        
        for emp in employees:
            print(f"\nEmpleado: {emp.user.email}")
            print(f"- Salario mensual: ${emp.contractual_monthly_salary}")
            print(f"- Frecuencia: {emp.payment_frequency}")
            
            # Test del método _calculate_fixed_salary_for_period
            from apps.employees_api.payments_views import PaymentViewSet
            viewset = PaymentViewSet()
            calculated = viewset._calculate_fixed_salary_for_period(emp)
            print(f"- Monto calculado por período: ${calculated}")
            
    except Exception as e:
        print(f"Error en test de lógica: {e}")

def test_earnings_summary_with_fixed():
    """Test de earnings_summary incluyendo empleados fijos"""
    print("\n=== TEST: Earnings Summary con Empleados Fijos ===")
    
    try:
        token = get_auth_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        # Llamar earnings_summary
        response = requests.get(f"{BASE_URL}/employees/payments/earnings_summary/", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            employees = data.get('employees', [])
            
            print(f"Total empleados en resumen: {len(employees)}")
            
            fixed_employees = [emp for emp in employees if emp['salary_type'] == 'fixed']
            print(f"Empleados fijos incluidos: {len(fixed_employees)}")
            
            for emp in fixed_employees:
                print(f"\n- {emp['employee_name']}")
                print(f"  Total ganado: ${emp['total_earned']}")
                print(f"  Estado: {emp['payment_status']}")
                print(f"  Servicios: {emp.get('services_count', 0)}")
                
        else:
            print(f"Error en earnings_summary: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error en test de earnings_summary: {e}")

def test_pay_fixed_employee():
    """Test de pago de empleado con sueldo fijo"""
    print("\n=== TEST: Pago de Empleado Fijo ===")
    
    try:
        token = get_auth_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        # Buscar empleado fijo
        tenant = Tenant.objects.get(name="alexander barber")
        fixed_employee = Employee.objects.filter(
            tenant=tenant,
            salary_type='fixed',
            is_active=True,
            contractual_monthly_salary__gt=0
        ).first()
        
        if not fixed_employee:
            print("No hay empleados fijos para probar")
            return
            
        print(f"Probando pago para: {fixed_employee.user.email}")
        
        # Intentar pago por quincena
        from datetime import datetime
        current_year = datetime.now().year
        current_fortnight = 24  # Quincena actual
        
        payload = {
            'employee_id': fixed_employee.id,
            'year': current_year,
            'fortnight': current_fortnight,
            'payment_method': 'cash',
            'payment_reference': f'TEST-FIXED-{fixed_employee.id}'
        }
        
        response = requests.post(f"{BASE_URL}/employees/payments/pay_employee/", 
                               json=payload, headers=headers)
        
        print(f"Respuesta del pago: {response.status_code}")
        if response.status_code in [200, 409]:  # 409 = ya pagado
            data = response.json()
            print(f"Estado: {data.get('status')}")
            print(f"Mensaje: {data.get('message')}")
            if 'summary' in data:
                summary = data['summary']
                print(f"Monto bruto: ${summary.get('gross_amount')}")
                print(f"Monto neto: ${summary.get('net_amount')}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error en test de pago: {e}")

def test_automatic_summary_creation():
    """Test de creación automática de FortnightSummary"""
    print("\n=== TEST: Creación Automática de Summary ===")
    
    try:
        tenant = Tenant.objects.get(name="alexander barber")
        fixed_employees = Employee.objects.filter(
            tenant=tenant,
            salary_type='fixed',
            is_active=True
        )
        
        from datetime import datetime
        current_year = datetime.now().year
        test_fortnight = 23  # Quincena anterior para test
        
        for emp in fixed_employees:
            # Verificar si existe summary
            existing = FortnightSummary.objects.filter(
                employee=emp,
                fortnight_year=current_year,
                fortnight_number=test_fortnight
            ).first()
            
            print(f"\nEmpleado: {emp.user.email}")
            print(f"Summary existente para {current_year}/{test_fortnight}: {'Sí' if existing else 'No'}")
            
            if existing:
                print(f"- Total earnings: ${existing.total_earnings}")
                print(f"- Pagado: {'Sí' if existing.is_paid else 'No'}")
                
    except Exception as e:
        print(f"Error en test de summary automático: {e}")

if __name__ == "__main__":
    print("Iniciando tests de cambios en sueldos fijos...\n")
    
    test_fixed_salary_logic()
    test_earnings_summary_with_fixed()
    test_pay_fixed_employee()
    test_automatic_summary_creation()
    
    print("\n=== Tests completados ===")