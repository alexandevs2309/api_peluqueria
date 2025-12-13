#!/usr/bin/env python3
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.employees_api.models import Employee
from apps.pos_api.models import Sale
from django.utils import timezone
from decimal import Decimal

User = get_user_model()

def create_test_sales():
    print('🧪 CREANDO VENTAS DE PRUEBA')
    
    user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
    employees = Employee.objects.filter(tenant=user.tenant, is_active=True)
    
    # Crear ventas pendientes para cada empleado
    for emp in employees:
        print(f'Creando ventas para {emp.user.full_name}...')
        
        # Crear 3 ventas pendientes
        for i in range(3):
            sale = Sale.objects.create(
                user=user,
                employee=emp,
                total=Decimal(f'{100 + (i * 50)}.00'),  # $100, $150, $200
                paid=Decimal(f'{100 + (i * 50)}.00'),
                status='completed',
                date_time=timezone.now(),
                period=None  # Esto las hace pendientes
            )
            print(f'  - Venta ${sale.total} creada')
    
    print('✅ Ventas de prueba creadas')

if __name__ == '__main__':
    create_test_sales()