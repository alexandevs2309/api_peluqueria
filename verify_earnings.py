#!/usr/bin/env python
"""Script para verificar y corregir datos de ganancias"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.pos_api.models import Sale
from django.db.models import Sum, Count
from datetime import datetime

def verify_earnings():
    print("=" * 60)
    print("VERIFICACIÓN DE GANANCIAS")
    print("=" * 60)
    
    # Obtener empleados activos
    employees = Employee.objects.filter(is_active=True).select_related('user')
    
    print(f"\nEmpleados activos: {employees.count()}")
    print("-" * 60)
    
    for emp in employees:
        print(f"\n{emp.user.full_name or emp.user.email}")
        print(f"  Email: {emp.user.email}")
        print(f"  Tipo de pago: {emp.salary_type}")
        print(f"  Comisión: {emp.commission_percentage}%")
        print(f"  Sueldo fijo: ${emp.salary_amount}")
        
        # Contar ventas del empleado
        sales = Sale.objects.filter(employee=emp, status='completed')
        sales_data = sales.aggregate(
            total_sales=Sum('total'),
            count=Count('id')
        )
        
        print(f"  Ventas totales: {sales_data['count']} ventas = ${sales_data['total_sales'] or 0}")
        
        # Calcular ganancias según tipo
        if emp.salary_type == 'commission':
            commission = float(sales_data['total_sales'] or 0) * float(emp.commission_percentage or 0) / 100
            print(f"  Ganancias por comisión: ${commission:.2f}")
        elif emp.salary_type == 'fixed':
            print(f"  Ganancias fijas: ${emp.salary_amount}")
        
        # Verificar ventas sin asignar
        unassigned = Sale.objects.filter(employee__isnull=True, status='completed').count()
        if unassigned > 0:
            print(f"\n⚠️  ADVERTENCIA: {unassigned} ventas sin empleado asignado")

if __name__ == '__main__':
    verify_earnings()
