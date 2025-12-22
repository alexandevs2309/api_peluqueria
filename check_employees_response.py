#!/usr/bin/env python
"""
Verificar respuesta del endpoint earnings_summary
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import RequestFactory
from apps.employees_api.payments_views import PaymentViewSet
from apps.auth_api.models import User

def check_employees_response():
    factory = RequestFactory()
    request = factory.get('/api/employees/payments/earnings_summary/')
    user = User.objects.filter(email='alexanderdelrosarioperez@gmail.com').first()
    request.user = user

    viewset = PaymentViewSet()
    response = viewset.earnings_summary(request)

    print('=== EMPLEADOS EN RESPUESTA ===')
    employees = response.data.get('employees', [])
    print(f'Total empleados: {len(employees)}')
    
    for emp in employees:
        print(f'{emp["employee_name"]} ({emp["salary_type"]}):')
        print(f'  Total ganado: ${emp["total_earned"]}')
        print(f'  Pendiente: ${emp["pending_amount"]}')
        print(f'  Sale IDs: {emp["pending_sale_ids"]}')
        print(f'  Estado: {emp["payment_status"]}')
        print()
    
    # Verificar empleados en DB
    from apps.employees_api.models import Employee
    all_employees = Employee.objects.filter(tenant=user.tenant, is_active=True)
    print(f'=== EMPLEADOS EN DB: {all_employees.count()} ===')
    for emp in all_employees:
        print(f'{emp.user.full_name} ({emp.salary_type})')

if __name__ == "__main__":
    check_employees_response()