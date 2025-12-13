#!/usr/bin/env python3
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.employees_api.models import Employee
from apps.pos_api.models import Sale
from apps.employees_api.payments_views import PaymentViewSet
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request

User = get_user_model()

def test_payment_calculation():
    print('🧮 TESTING CÁLCULOS DE PAGO')
    
    user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
    employees = Employee.objects.filter(tenant=user.tenant, is_active=True)
    
    # Crear instancia del ViewSet
    viewset = PaymentViewSet()
    
    for emp in employees:
        print(f'\n👤 {emp.user.full_name} ({emp.salary_type})')
        
        # Obtener ventas pendientes
        pending_sales = Sale.objects.filter(
            employee=emp,
            period__isnull=True,
            status='completed'
        )
        
        if pending_sales.exists():
            total_sales = sum(float(s.total) for s in pending_sales)
            print(f'   Ventas pendientes: ${total_sales}')
            
            # Calcular monto usando la función corregida
            amount = viewset._calculate_payment_amount(emp, total_sales)
            print(f'   Monto calculado: ${amount:.2f}')
            
            # Verificar cálculo manual
            if emp.salary_type == 'commission':
                expected = total_sales * float(emp.commission_percentage) / 100
                print(f'   Esperado (comisión): ${expected:.2f}')
            elif emp.salary_type == 'fixed':
                expected = float(emp.contractual_monthly_salary or emp.salary_amount) / 2
                print(f'   Esperado (fijo quincenal): ${expected:.2f}')
            elif emp.salary_type == 'mixed':
                commission = total_sales * float(emp.commission_percentage) / 100
                base = float(emp.contractual_monthly_salary or emp.salary_amount) / 2
                expected = base + commission
                print(f'   Esperado (mixto): ${base:.2f} + ${commission:.2f} = ${expected:.2f}')
            
            # Verificar si coinciden
            if abs(amount - expected) < 0.01:
                print('   ✅ Cálculo correcto')
            else:
                print(f'   ❌ Error en cálculo: {amount} vs {expected}')

def test_pending_payments_endpoint():
    print('\n📡 TESTING ENDPOINT pending_payments')
    
    user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
    
    # Simular request
    factory = APIRequestFactory()
    request = factory.get('/api/employees/payments/pending_payments/')
    request.user = user
    
    viewset = PaymentViewSet()
    response = viewset.pending_payments(Request(request))
    
    print('Status:', response.status_code)
    if response.status_code == 200:
        data = response.data
        print('Empleados con pendientes:', data.get('total_employees', 0))
        print('Monto total pendiente:', data.get('total_amount', 0))
        
        for payment in data.get('pending_payments', []):
            print(f'- {payment.get("employee_name")}: ${payment.get("total_amount")}')

if __name__ == '__main__':
    test_payment_calculation()
    test_pending_payments_endpoint()