#!/usr/bin/env python3
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.employees_api.models import Employee
from apps.pos_api.models import Sale
from apps.employees_api.earnings_models import FortnightSummary
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

User = get_user_model()

def manual_payment():
    print('💳 PAGO MANUAL - SANDY')
    
    user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
    sandy = Employee.objects.get(user__full_name='sandy de la cruz', tenant=user.tenant)
    
    # Obtener ventas pendientes
    pending_sales = Sale.objects.filter(employee=sandy, period__isnull=True, status='completed')
    
    if not pending_sales.exists():
        print('❌ No hay ventas pendientes')
        return
    
    total_sales = sum(float(s.total) for s in pending_sales)
    commission_amount = Decimal(str(total_sales * float(sandy.commission_percentage) / 100))
    
    print(f'Total ventas: ${total_sales}')
    print(f'Comisión (60%): ${commission_amount}')
    
    # Calcular período actual
    today = timezone.now().date()
    year = today.year
    month = today.month
    day = today.day
    fortnight_in_month = 1 if day <= 15 else 2
    fortnight = (month - 1) * 2 + fortnight_in_month
    
    with transaction.atomic():
        # Crear o obtener summary
        summary, created = FortnightSummary.objects.get_or_create(
            employee=sandy,
            fortnight_year=year,
            fortnight_number=fortnight,
            defaults={
                'total_earnings': Decimal('0.00'),
                'total_services': 0,
                'is_paid': False
            }
        )
        
        # Actualizar summary
        summary.total_earnings += commission_amount
        summary.total_services += pending_sales.count()
        
        # Asignar ventas al summary
        for sale in pending_sales:
            sale.period = summary
            sale.save()
        
        # Marcar como pagado
        summary.is_paid = True
        summary.paid_at = timezone.now()
        summary.paid_by = user
        summary.payment_method = 'cash'
        summary.payment_reference = 'TEST-MANUAL-001'
        summary.amount_paid = commission_amount
        summary.save()
        
        print(f'✅ PAGO COMPLETADO: ${commission_amount}')
    
    # Verificar resultado
    remaining = Sale.objects.filter(
        employee__tenant=user.tenant, 
        period__isnull=True, 
        status='completed'
    ).count()
    print(f'Ventas pendientes restantes: {remaining}')

if __name__ == '__main__':
    manual_payment()