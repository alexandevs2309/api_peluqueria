#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.payroll_api.client_views import ClientPayrollViewSet
from apps.employees_api.models import Employee
from django.contrib.auth import get_user_model
from unittest.mock import Mock

print('=== PRUEBA CLIENT PAYROLL VIEWSET ===')

# Obtener empleado y usuario
employee = Employee.objects.get(id=4)
user = employee.user

print(f'Empleado: {employee.user.email}')
print(f'Tenant: {employee.tenant}')
print(f'Salary type: {employee.salary_type}')
print(f'Payment mode: {employee.commission_payment_mode}')

# Crear mock request
request = Mock()
request.user = user

# Crear viewset
viewset = ClientPayrollViewSet()
viewset.request = request

# Probar método list
response = viewset.list(request)
periods = response.data.get('periods', [])

print(f'Períodos encontrados: {len(periods)}')

for period in periods:
    if period['employee_name'] == employee.user.email or employee.user.full_name in period['employee_name']:
        print(f'✅ Empleado encontrado en período:')
        print(f'   Período: {period["period_display"]}')
        print(f'   Estado: {period["status"]}')
        print(f'   Monto bruto: ${period["gross_amount"]}')
        print(f'   Monto neto: ${period["net_amount"]}')
        break
else:
    print('❌ Empleado NO encontrado en períodos')

print('=== PRUEBA COMPLETADA ===')