#!/usr/bin/env python
"""
Crear ventas grandes para empleados por comisión
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.pos_api.models import Sale
from apps.auth_api.models import User
from datetime import datetime
from decimal import Decimal

def create_large_sales():
    user = User.objects.filter(email='alexanderdelrosarioperez@gmail.com').first()
    commission_employees = Employee.objects.filter(
        tenant=user.tenant, 
        salary_type='commission',
        is_active=True
    )

    for employee in commission_employees:
        print(f'Creando ventas grandes para: {employee.user.full_name}')
        
        # Crear 3 ventas grandes en el período actual
        sales_data = [
            {'amount': 15000, 'date': datetime(2025, 12, 5, 14, 0, 0)},
            {'amount': 12000, 'date': datetime(2025, 12, 8, 16, 30, 0)},
            {'amount': 8000, 'date': datetime(2025, 12, 12, 11, 15, 0)}
        ]
        
        total_sales = 0
        for i, sale_data in enumerate(sales_data, 1):
            sale = Sale.objects.create(
                employee=employee,
                total=Decimal(str(sale_data['amount'])),
                paid=Decimal(str(sale_data['amount'])),
                status='completed',
                date_time=sale_data['date'],
                payment_method='cash'
            )
            total_sales += sale_data['amount']
            print(f'  ✅ Venta {i}: ${sale_data["amount"]} ({sale_data["date"].strftime("%d %b")})')
        
        # Calcular comisión esperada
        commission_rate = float(employee.commission_percentage)
        expected_commission = total_sales * (commission_rate / 100)
        
        print(f'  📊 Total ventas: ${total_sales}')
        print(f'  💰 Comisión esperada ({commission_rate}%): ${expected_commission}')
        print()

if __name__ == "__main__":
    create_large_sales()