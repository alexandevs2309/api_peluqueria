#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.pos_api.models import Sale
from apps.employees_api.models import Employee
from datetime import date

today = date.today()
sales = Sale.objects.filter(date_time__date=today, status='completed')
print('=== VENTAS HOY ===')
for s in sales:
    print(f'Sale {s.id}: ${s.total}, employee={s.employee_id}')

print('\n=== EMPLEADOS ===')
employees = Employee.objects.filter(is_active=True)
for e in employees:
    print(f'Employee {e.id}: {e.user.full_name}')
    print(f'  Type: {e.salary_type}, Commission: {e.commission_percentage}%')
    print(f'  Salary: ${e.contractual_monthly_salary}, Freq: {e.payment_frequency}')
    print(f'  Deductions: AFP={e.apply_afp}, SFS={e.apply_sfs}, ISR={e.apply_isr}')
