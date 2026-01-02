#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import Earning
from apps.services_api.models import ServiceEmployee

print('=== DIAGNÓSTICO: EARNINGS PARA EMPLEADOS FIJOS ===')

# 1. REVISAR CONFIGURACIÓN DE EMPLEADOS ESPECÍFICOS
target_emails = ['radhamerosario@gmail.com', 'a.nicole.amejia@gmail.com']

print('\n1. CONFIGURACIÓN DE EMPLEADOS:')
print('=' * 50)

for email in target_emails:
    try:
        employee = Employee.objects.get(user__email=email)
        print(f'\nEmpleado: {email}')
        print(f'  ID: {employee.id}')
        print(f'  salary_type: {employee.salary_type}')
        print(f'  commission_payment_mode: {employee.commission_payment_mode}')
        print(f'  commission_percentage: {employee.commission_percentage}%')
        print(f'  salary_amount: ${employee.salary_amount}')
        print(f'  is_active: {employee.is_active}')
    except Employee.DoesNotExist:
        print(f'\n❌ Empleado {email} no encontrado')

# 2. REVISAR EARNINGS RECIENTES
print('\n\n2. EARNINGS RECIENTES (últimos 5):')
print('=' * 50)

recent_earnings = Earning.objects.filter(
    employee__user__email__in=target_emails
).order_by('-created_at')[:5]

for earning in recent_earnings:
    print(f'\nEarning ID: {earning.id}')
    print(f'  Empleado: {earning.employee.user.email}')
    print(f'  Monto: ${earning.amount}')
    print(f'  Tipo: {earning.earning_type}')
    print(f'  Porcentaje: {earning.percentage}%')
    print(f'  Fecha: {earning.created_at}')
    print(f'  Descripción: {earning.description}')
    print(f'  Sale ID: {earning.sale_id if earning.sale else "N/A"}')

# 3. REVISAR RELACIONES ServiceEmployee
print('\n\n3. RELACIONES ServiceEmployee:')
print('=' * 50)

for email in target_emails:
    try:
        employee = Employee.objects.get(user__email=email)
        service_relations = ServiceEmployee.objects.filter(employee=employee)
        
        print(f'\nEmpleado: {email}')
        print(f'  Servicios asignados: {service_relations.count()}')
        
        for relation in service_relations:
            print(f'    - Servicio: {relation.service.name}')
            print(f'      Commission %: {relation.commission_percentage}%')
            print(f'      Custom price: ${relation.custom_price or "N/A"}')
            
    except Employee.DoesNotExist:
        continue

# 4. ANÁLISIS DE REGLAS ACTUALES
print('\n\n4. ANÁLISIS DE REGLAS ACTUALES:')
print('=' * 50)

print('\nReglas observadas en el código actual:')
print('- Se crean earnings si employee.salary_type in ["commission", "mixed"]')
print('- Se crean earnings si employee.commission_payment_mode == "PER_PERIOD"')
print('- Se busca ServiceEmployee para obtener porcentaje específico')
print('- Fallback: usa employee.commission_percentage si no hay ServiceEmployee')

print('\n\n5. DIAGNÓSTICO:')
print('=' * 50)

for email in target_emails:
    try:
        employee = Employee.objects.get(user__email=email)
        
        print(f'\nEmpleado: {email}')
        
        # Verificar si debería recibir comisiones según configuración actual
        should_get_commission = (
            employee.salary_type in ['commission', 'mixed'] and
            employee.commission_payment_mode == 'PER_PERIOD'
        )
        
        print(f'  ¿Debería recibir comisiones según reglas actuales? {should_get_commission}')
        
        if employee.salary_type == 'fixed':
            print('  ⚠️  PROBLEMA: salary_type=fixed pero recibió earnings')
        
        # Verificar ServiceEmployee
        has_service_relations = ServiceEmployee.objects.filter(employee=employee).exists()
        print(f'  ¿Tiene servicios asignados? {has_service_relations}')
        
        if has_service_relations and employee.salary_type == 'fixed':
            print('  ⚠️  CONFLICTO: Empleado fijo con servicios asignados')
            
    except Employee.DoesNotExist:
        continue

print('\n=== DIAGNÓSTICO COMPLETADO ===')