#!/usr/bin/env python
"""
Script para corregir datos de earnings:
1. Actualizar sueldo mensual a quincenal (dividir entre 2)
2. Asignar ventas sin empleado al empleado por comisión
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.pos_api.models import Sale
from django.db import connection

# Cambiar al schema del tenant
connection.set_schema('alexanderbarber7')

print("=== CORRECCIÓN DE DATOS DE EARNINGS ===\n")

# 1. Corregir sueldos mensuales a quincenales
print("1. Corrigiendo sueldos mensuales a quincenales...")
employees_fixed = Employee.objects.filter(salary_type='fixed', salary_amount__gt=0)
for emp in employees_fixed:
    old_salary = float(emp.salary_amount)
    # Si el sueldo es mayor a 20,000, probablemente es mensual
    if old_salary > 20000:
        new_salary = old_salary / 2
        print(f"   - {emp.user.full_name or emp.user.email}: ${old_salary:,.2f} -> ${new_salary:,.2f} (quincenal)")
        emp.salary_amount = new_salary
        emp.save()
    else:
        print(f"   - {emp.user.full_name or emp.user.email}: ${old_salary:,.2f} (ya es quincenal)")

# 2. Asignar ventas sin empleado
print("\n2. Asignando ventas sin empleado...")
sales_without_employee = Sale.objects.filter(employee__isnull=True)
print(f"   Total ventas sin empleado: {sales_without_employee.count()}")

if sales_without_employee.exists():
    # Buscar empleado por comisión (stylist)
    stylist = Employee.objects.filter(salary_type='commission', is_active=True).first()
    
    if stylist:
        print(f"   Asignando a: {stylist.user.full_name or stylist.user.email}")
        count = sales_without_employee.update(employee=stylist)
        print(f"   ✓ {count} ventas asignadas")
    else:
        print("   ⚠ No se encontró empleado por comisión activo")
else:
    print("   ✓ No hay ventas sin empleado")

print("\n=== CORRECCIÓN COMPLETADA ===")
