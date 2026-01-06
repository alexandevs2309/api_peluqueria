#!/usr/bin/env python3
import os
import sys
import django

sys.path.append('/home/alexander/Escritorio/clone/api_peluqueria-master')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee

print('🔍 INCONSISTENCIA ENCONTRADA:')
print('=' * 50)

employee = Employee.objects.filter(salary_type='fixed').first()
print(f'Empleado: {employee.user.email}')
print(f'salary_type: {employee.salary_type}')
print()

print('BACKEND (PayrollSettlementService usa):')
print(f'   employee.salary_amount = ${employee.salary_amount}')
print()

print('FRONTEND (configura):')
print(f'   employee.contractual_monthly_salary = ${employee.contractual_monthly_salary}')
print()

print('RESULTADO:')
print(f'   Backend calcula: ${employee.salary_amount} (CERO)')
print(f'   Debería usar: ${employee.contractual_monthly_salary} (VALOR REAL)')