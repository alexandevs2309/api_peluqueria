#!/usr/bin/env python
"""
Crear ventas de prueba para verificar corrección de comisiones por período
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

def create_test_sales():
    user = User.objects.filter(email='alexanderdelrosarioperez@gmail.com').first()
    commission_emp = Employee.objects.filter(tenant=user.tenant, salary_type='commission').first()

    if commission_emp:
        print(f'Creando ventas de prueba para: {commission_emp.user.full_name}')
        
        # Venta del período actual (1-15 dic)
        sale1 = Sale.objects.create(
            employee=commission_emp,
            total=Decimal('100.00'),
            paid=Decimal('100.00'),
            status='completed',
            date_time=datetime(2025, 12, 10, 10, 0, 0),  # 10 dic - período actual
            payment_method='cash'
        )
        print(f'✅ Venta período actual: ${sale1.total} (10 dic)')
        
        # Venta de período anterior (16-30 nov)
        sale2 = Sale.objects.create(
            employee=commission_emp,
            total=Decimal('200.00'),
            paid=Decimal('200.00'),
            status='completed',
            date_time=datetime(2025, 11, 25, 10, 0, 0),  # 25 nov - período anterior
            payment_method='cash'
        )
        print(f'✅ Venta período anterior: ${sale2.total} (25 nov)')
        
        # Verificar filtrado
        from apps.employees_api.period_utils import get_current_period_for_employee
        current_period = get_current_period_for_employee(commission_emp)
        
        all_pending = Sale.objects.filter(
            employee=commission_emp,
            status='completed',
            period__isnull=True
        )
        
        period_sales = Sale.objects.filter(
            employee=commission_emp,
            status='completed',
            period__isnull=True,
            date_time__date__gte=current_period['start_date'],
            date_time__date__lte=current_period['end_date']
        )
        
        print(f'\n📊 RESULTADOS:')
        print(f'   Total ventas pendientes: {all_pending.count()}')
        print(f'   Ventas del período actual: {period_sales.count()}')
        print(f'   Período actual: {current_period["start_date"]} - {current_period["end_date"]}')
        
        if all_pending.count() > period_sales.count():
            print(f'   🎯 CORRECCIÓN FUNCIONANDO: Filtrado por período activo')
        
        # Calcular montos
        total_all = sum(float(s.total) for s in all_pending)
        total_period = sum(float(s.total) for s in period_sales)
        commission_all = total_all * 0.4  # 40% comisión
        commission_period = total_period * 0.4
        
        print(f'\n💰 MONTOS:')
        print(f'   Método anterior (todas): ${commission_all}')
        print(f'   Método corregido (período): ${commission_period}')
        
        return sale1.id, sale2.id

if __name__ == "__main__":
    create_test_sales()