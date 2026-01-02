#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.payroll_api.services import PayrollSettlementService
from apps.employees_api.models import Employee

print('=== PRUEBA PAYROLL SERVICE ===')

employee = Employee.objects.get(id=4)
print(f'Empleado: {employee.user.email}')

# Probar el servicio de payroll
service = PayrollSettlementService()
periods = service.get_periods_with_pending_earnings(employee.tenant)

print(f'Períodos con earnings pendientes: {len(periods)}')

for period in periods:
    print(f'Período: {period["period_display"]}')
    print(f'Empleados: {len(period["employees"])}')
    
    for emp_data in period["employees"]:
        if emp_data["employee_id"] == employee.id:
            print(f'  ✅ Empleado encontrado: {emp_data["employee_name"]}')
            print(f'     Earnings: {emp_data["total_earnings"]}')
            print(f'     Monto: ${emp_data["total_amount"]}')
            break
    else:
        print(f'  ❌ Empleado NO encontrado en este período')

print('=== PRUEBA COMPLETADA ===')