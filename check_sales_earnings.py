#!/usr/bin/env python
"""
Verificar por qué las ventas no generan ganancias
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.pos_api.models import Sale
from apps.employees_api.models import Employee

def check_sales_earnings():
    # Verificar ventas recientes
    recent_sales = Sale.objects.filter(status='completed').order_by('-id')[:5]
    print('=== VENTAS RECIENTES ===')
    for sale in recent_sales:
        print(f'Venta {sale.id}: ${sale.total} - {sale.employee.user.full_name if sale.employee else "Sin empleado"} - {sale.date_time}')
        print(f'  Status: {sale.status}, Period: {sale.period}')
        
        # Verificar si tiene earnings
        earnings = sale.earnings.all()
        print(f'  Earnings: {earnings.count()} registros')
        for earning in earnings:
            print(f'    - ${earning.amount} ({earning.earning_type})')
        print()

    # Verificar empleados y sus ventas pendientes
    employees = Employee.objects.filter(is_active=True)
    print('=== EMPLEADOS Y VENTAS PENDIENTES ===')
    for emp in employees:
        pending_sales = Sale.objects.filter(
            employee=emp,
            status='completed',
            period__isnull=True
        )
        print(f'{emp.user.full_name}: {pending_sales.count()} ventas pendientes')
        for sale in pending_sales[:3]:
            print(f'  - Venta {sale.id}: ${sale.total} ({sale.date_time.date()})')
        print()

if __name__ == "__main__":
    check_sales_earnings()