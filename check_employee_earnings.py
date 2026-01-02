#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import Earning

employee = Employee.objects.get(id=4)
earnings = Earning.objects.filter(employee=employee)

print(f'Empleado: {employee.user.email}')
print(f'Total earnings del empleado: {earnings.count()}')
print(f'Suma total: ${sum(e.amount for e in earnings)}')

# Verificar último earning
last_earning = earnings.order_by('-created_at').first()
if last_earning:
    print(f'Último earning: ${last_earning.amount} - {last_earning.description}')
    print(f'Fecha: {last_earning.created_at}')
    print(f'Quincena: {last_earning.fortnight_display}')