#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.billing_api.models import Invoice
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan
from django.db.models import Sum

print('=== DATOS ACTUALES ===')
print(f'Tenants: {Tenant.objects.count()} (Activos: {Tenant.objects.filter(is_active=True).count()})')
print(f'Facturas: {Invoice.objects.count()} (Pagadas: {Invoice.objects.filter(is_paid=True).count()})')
print(f'Planes: {SubscriptionPlan.objects.count()}')

# MRR actual
mrr = Invoice.objects.filter(is_paid=True).aggregate(total=Sum('amount'))['total'] or 0
print(f'MRR Total: ${mrr}')

# Mostrar algunas facturas
print('\n=== FACTURAS RECIENTES ===')
for invoice in Invoice.objects.order_by('-issued_at')[:3]:
    print(f'#{invoice.id}: ${invoice.amount} - {invoice.user.email} - Pagada: {invoice.is_paid}')