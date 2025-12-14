#!/usr/bin/env python3
"""
Test simplificado para validar cambios en sueldos fijos
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

def get_auth_token():
    """Obtener token de autenticación"""
    response = requests.post(f"{BASE_URL}/api/auth/login/", json={
        'email': 'alexanderdelrosarioperez@gmail.com',
        'password': 'baspeka1394'
    })
    if response.status_code == 200:
        return response.json().get('access_token')
    raise Exception(f"Login failed: {response.status_code}")

def test_fixed_salary_calculation():
    """Test directo de cálculo de sueldos fijos"""
    print("=== TEST: Cálculo de Sueldos Fijos ===")
    
    try:
        # Buscar tenant correcto
        tenant = Tenant.objects.get(name="alexander  barber")  # Nota el doble espacio
        print(f"Tenant encontrado: {tenant.name}")
        
        # Buscar empleados
        employees = Employee.objects.filter(tenant=tenant, is_active=True)
        print(f"Total empleados activos: {employees.count()}")
        
        # Verificar empleados con sueldo fijo
        fixed_employees = employees.filter(salary_type='fixed')
        print(f"Empleados con sueldo fijo: {fixed_employees.count()}")
        
        # Test del método de cálculo
        from apps.employees_api.payments_views import PaymentViewSet
        viewset = PaymentViewSet()
        
        for emp in employees:
            print(f"\n--- Empleado: {emp.user.email} ---")
            print(f"Tipo salario: {emp.salary_type}")
            print(f"Salario mensual: ${emp.contractual_monthly_salary or 0}")
            print(f"Frecuencia pago: {getattr(emp, 'payment_frequency', 'N/A')}")
            
            if emp.salary_type in ['fixed', 'mixed']:
                calculated = viewset._calculate_fixed_salary_for_period(emp)
                print(f"Monto calculado por período: ${calculated}")
                
                # Test de cálculo con ventas (para mixed)
                if emp.salary_type == 'mixed':
                    total_with_sales = viewset._calculate_payment_amount(emp, 1000)  # $1000 en ventas
                    print(f"Con $1000 en ventas: ${total_with_sales}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_earnings_summary_api():
    """Test del API earnings_summary"""
    print("\n=== TEST: API Earnings Summary ===")
    
    try:
        token = get_auth_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.get(f"{BASE_URL}/api/employees/payments/earnings_summary/", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            employees = data.get('employees', [])
            
            print(f"Empleados en resumen: {len(employees)}")
            
            for emp in employees:
                print(f"\n- {emp['employee_name']}")
                print(f"  Tipo: {emp['salary_type']}")
                print(f"  Total ganado: ${emp['total_earned']}")
                print(f"  Pendiente: ${emp.get('pending_amount', 0)}")
                print(f"  Estado: {emp['payment_status']}")
                
            return True
        else:
            print(f"Error API: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_summary_creation():
    """Test de creación automática de FortnightSummary"""
    print("\n=== TEST: Creación Automática de Summary ===")
    
    try:
        tenant = Tenant.objects.get(name="alexander  barber")
        
        # Contar summaries antes
        before_count = FortnightSummary.objects.filter(employee__tenant=tenant).count()
        print(f"FortnightSummary existentes: {before_count}")
        
        # Llamar earnings_summary para trigger creación automática
        token = get_auth_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.get(f"{BASE_URL}/api/employees/payments/earnings_summary/", headers=headers)
        
        # Contar summaries después
        after_count = FortnightSummary.objects.filter(employee__tenant=tenant).count()
        print(f"FortnightSummary después: {after_count}")
        
        if after_count > before_count:
            print(f"✅ Se crearon {after_count - before_count} summaries automáticamente")
            
            # Mostrar summaries creados para empleados fijos
            new_summaries = FortnightSummary.objects.filter(
                employee__tenant=tenant,
                employee__salary_type='fixed'
            ).order_by('-id')[:3]
            
            for summary in new_summaries:
                print(f"- {summary.employee.user.email}: ${summary.total_earnings}")
                
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Iniciando tests simplificados...\n")
    
    success = True
    success &= test_fixed_salary_calculation()
    success &= test_earnings_summary_api()
    success &= test_summary_creation()
    
    print(f"\n=== Resultado: {'✅ ÉXITO' if success else '❌ FALLÓ'} ===")