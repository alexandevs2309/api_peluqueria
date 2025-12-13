#!/usr/bin/env python
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.pos_api.models import Sale
from apps.employees_api.models import Employee

yesther = Employee.objects.filter(user__email='yestherdelosantos1@hmail.com').first()
if yesther:
    sales = Sale.objects.filter(employee=yesther, status='completed').order_by('date_time')
    print(f'Ventas de Yesther ({sales.count()} ventas):')
    for sale in sales:
        print(f'  - {sale.date_time.date()} | ${sale.total}')
