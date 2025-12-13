#!/usr/bin/env python
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.pos_api.models import Sale
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import FortnightSummary
from django.db.models import Sum, Count
from datetime import datetime

# Yesther
yesther = Employee.objects.filter(user__email='yestherdelosantos1@hmail.com').first()
if yesther:
    print(f'Yesther ID: {yesther.id}')
    print(f'Tipo: {yesther.salary_type}')
    print(f'Comisión: {yesther.commission_percentage}%')
    
    # Ventas totales
    sales = Sale.objects.filter(employee=yesther, status='completed')
    data = sales.aggregate(total=Sum('total'), count=Count('id'))
    print(f'\nVentas totales: {data["count"]} = ${data["total"]}')
    print(f'Comisión calculada: ${float(data["total"] or 0) * float(yesther.commission_percentage) / 100}')
    
    # Ventas de la quincena actual (2025, quincena 1)
    year = 2025
    fortnight = 1
    month = ((fortnight - 1) // 2) + 1
    is_first_half = (fortnight % 2) == 1
    
    if is_first_half:
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, 15).date()
    else:
        start_date = datetime(year, month, 16).date()
        end_date = datetime(year, month, 31).date()
    
    print(f'\nQuincena {fortnight} de {year}: {start_date} a {end_date}')
    
    sales_period = Sale.objects.filter(
        employee=yesther,
        date_time__date__gte=start_date,
        date_time__date__lte=end_date,
        status='completed'
    )
    data_period = sales_period.aggregate(total=Sum('total'), count=Count('id'))
    print(f'Ventas del período: {data_period["count"]} = ${data_period["total"]}')
    
    # FortnightSummary
    summary = FortnightSummary.objects.filter(
        employee=yesther,
        fortnight_year=year,
        fortnight_number=fortnight
    ).first()
    
    if summary:
        print(f'\nFortnightSummary existe:')
        print(f'  Total earnings: ${summary.total_earnings}')
        print(f'  Total services: {summary.total_services}')
        print(f'  Is paid: {summary.is_paid}')
    else:
        print(f'\nFortnightSummary NO existe para esta quincena')
