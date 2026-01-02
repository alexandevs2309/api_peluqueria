#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import Earning

print('=== BÚSQUEDA DE EMPLEADOS FIJOS CON EARNINGS ===')

# 1. BUSCAR TODOS LOS EMPLEADOS POR TIPO
print('\n1. EMPLEADOS POR SALARY_TYPE:')
print('=' * 40)

for salary_type in ['fixed', 'commission', 'mixed']:
    count = Employee.objects.filter(salary_type=salary_type).count()
    print(f'{salary_type}: {count} empleados')

# 2. LISTAR EMPLEADOS FIJOS
print('\n2. EMPLEADOS CON SALARY_TYPE=FIXED:')
print('=' * 40)

fixed_employees = Employee.objects.filter(salary_type='fixed')
for emp in fixed_employees:
    print(f'- {emp.user.email} (ID: {emp.id})')
    print(f'  commission_payment_mode: {emp.commission_payment_mode}')
    print(f'  commission_percentage: {emp.commission_percentage}%')

# 3. BUSCAR EARNINGS DE EMPLEADOS FIJOS
print('\n3. EARNINGS DE EMPLEADOS FIJOS:')
print('=' * 40)

fixed_earnings = Earning.objects.filter(employee__salary_type='fixed')
print(f'Total earnings de empleados fijos: {fixed_earnings.count()}')

if fixed_earnings.exists():
    print('\n⚠️  PROBLEMA ENCONTRADO: Empleados fijos con earnings')
    for earning in fixed_earnings.order_by('-created_at')[:5]:
        print(f'\nEarning ID: {earning.id}')
        print(f'  Empleado: {earning.employee.user.email}')
        print(f'  Salary type: {earning.employee.salary_type}')
        print(f'  Monto: ${earning.amount}')
        print(f'  Fecha: {earning.created_at}')
        print(f'  Descripción: {earning.description}')
else:
    print('✅ No se encontraron earnings para empleados fijos')

# 4. VERIFICAR REGLA ACTUAL EN EL CÓDIGO
print('\n4. VERIFICACIÓN DE REGLA ACTUAL:')
print('=' * 40)

print('Regla en _create_employee_earning:')
print('- if employee.salary_type not in ["commission", "mixed"]: continue')
print('- if employee.commission_payment_mode != "PER_PERIOD": continue')

print('\nEmpleados que DEBERÍAN recibir earnings según regla actual:')
eligible_employees = Employee.objects.filter(
    salary_type__in=['commission', 'mixed'],
    commission_payment_mode='PER_PERIOD',
    is_active=True
)

for emp in eligible_employees:
    print(f'- {emp.user.email}: {emp.salary_type}, {emp.commission_payment_mode}')

print('\nEmpleados que NO deberían recibir earnings:')
non_eligible = Employee.objects.filter(
    is_active=True
).exclude(
    salary_type__in=['commission', 'mixed'],
    commission_payment_mode='PER_PERIOD'
)

for emp in non_eligible:
    print(f'- {emp.user.email}: {emp.salary_type}, {emp.commission_payment_mode}')

print('\n=== BÚSQUEDA COMPLETADA ===')