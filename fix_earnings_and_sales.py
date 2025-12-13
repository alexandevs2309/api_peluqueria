#!/usr/bin/env python
"""
Script para corregir datos:
1. Convertir salario mensual a quincenal (Juan: $30,000 -> $15,000)
2. Asignar ventas sin empleado a Yesther
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.pos_api.models import Sale
from django.db import connection

# Usar tenant
tenant_schema = 'alexanderbarber7'
connection.set_schema(tenant_schema)

print(f"=== CORRECCIÓN DE DATOS - Tenant: {tenant_schema} ===\n")

# 1. Corregir salario de Juan (mensual -> quincenal)
print("1. Corrigiendo salarios mensuales a quincenales...")
juan = Employee.objects.filter(user__email__icontains='juan').first()
if juan:
    old_salary = float(juan.salary_amount)
    if old_salary >= 20000:  # Probablemente es mensual
        new_salary = old_salary / 2
        juan.salary_amount = new_salary
        juan.save()
        print(f"   ✓ {juan.user.full_name}: ${old_salary:,.2f} -> ${new_salary:,.2f} (quincenal)")
    else:
        print(f"   - {juan.user.full_name}: ${old_salary:,.2f} (ya es quincenal)")
else:
    print("   ⚠ Juan no encontrado")

# 2. Asignar ventas sin empleado a Yesther
print("\n2. Asignando ventas sin empleado a Yesther...")
yesther = Employee.objects.filter(user__email__icontains='yesther').first()
if yesther:
    sales_without_employee = Sale.objects.filter(employee__isnull=True)
    count = sales_without_employee.count()
    
    if count > 0:
        total_amount = sum(float(s.total) for s in sales_without_employee)
        sales_without_employee.update(employee=yesther)
        print(f"   ✓ {count} ventas asignadas a {yesther.user.full_name}")
        print(f"   ✓ Total: ${total_amount:,.2f}")
        
        # Calcular comisión
        commission_rate = float(yesther.commission_percentage or 60)
        commission = total_amount * (commission_rate / 100)
        print(f"   ✓ Comisión ({commission_rate}%): ${commission:,.2f}")
    else:
        print("   - No hay ventas sin empleado")
else:
    print("   ⚠ Yesther no encontrada")

print("\n=== CORRECCIÓN COMPLETADA ===")
print("\nPróximos pasos:")
print("1. Verificar en el frontend que los datos se muestren correctamente")
print("2. Procesar pago para ver descuentos AFP, SFS, ISR aplicados")
