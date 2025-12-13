#!/usr/bin/env python3
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

def test_endpoint():
    print('📡 TESTING ENDPOINT earnings_summary')
    
    client = Client()
    user = get_user_model().objects.get(email='alexanderdelrosarioperez@gmail.com')
    client.force_login(user)
    
    response = client.get('/api/employees/payments/earnings_summary/')
    print('Status:', response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        print('Empleados encontrados:', len(data.get('employees', [])))
        
        for emp in data.get('employees', []):
            name = emp.get('employee_name')
            total = emp.get('total_earned')
            pending = emp.get('pending_amount', 'N/A')
            status = emp.get('payment_status')
            print(f'- {name}: Total=${total}, Pendiente=${pending}, Status={status}')
        
        pending_summary = data.get('pending_summary', {})
        total_emp = pending_summary.get('total_employees', 0)
        total_amt = pending_summary.get('total_amount', 0)
        print(f'Resumen pendientes: {total_emp} empleados, ${total_amt}')
    else:
        print('Error:', response.content.decode())

if __name__ == '__main__':
    test_endpoint()