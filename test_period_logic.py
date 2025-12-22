#!/usr/bin/env python
"""
Probar nueva lógica de asignación de períodos
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.pos_api.models import Sale
from apps.employees_api.models import Employee
from datetime import datetime
from decimal import Decimal
from django.utils import timezone

def test_period_logic():
    # Buscar Yesther
    yesther = Employee.objects.filter(user__full_name__icontains='Yesther').first()
    if yesther:
        print(f'=== PROBANDO NUEVA LÓGICA PARA {yesther.user.full_name} ===')
        
        # Verificar estado actual
        from apps.employees_api.earnings_models import FortnightSummary
        current_summary = FortnightSummary.objects.filter(
            employee=yesther,
            fortnight_year=2025,
            fortnight_number=23
        ).first()
        
        print(f'Período actual (2025/23): Pagado={current_summary.is_paid if current_summary else "No existe"}')
        
        # Simular creación de venta usando la lógica del POS
        from apps.pos_api.views import SaleViewSet
        sale_viewset = SaleViewSet()
        
        # Obtener período activo usando la nueva lógica
        active_period = sale_viewset._get_or_create_active_period(yesther)
        
        print(f'Período activo obtenido: {active_period.fortnight_year}/{active_period.fortnight_number}')
        print(f'¿Está pagado?: {active_period.is_paid}')
        
        # Crear nueva venta asignada al período correcto
        new_sale = Sale.objects.create(
            employee=yesther,
            period=active_period,
            total=Decimal('500.00'),
            paid=Decimal('500.00'),
            status='completed',
            date_time=timezone.now(),
            payment_method='cash'
        )
        
        print(f'Nueva venta creada: ID={new_sale.id}, Total=${new_sale.total}')
        print(f'Asignada al período: {new_sale.period.fortnight_year}/{new_sale.period.fortnight_number}')
        
        # Verificar que ahora aparece como pendiente
        print('\n=== VERIFICANDO EARNINGS_SUMMARY ===')
        from django.test import RequestFactory
        from apps.employees_api.payments_views import PaymentViewSet
        from apps.auth_api.models import User
        
        factory = RequestFactory()
        request = factory.get('/api/employees/payments/earnings_summary/')
        user = User.objects.filter(email='alexanderdelrosarioperez@gmail.com').first()
        request.user = user
        
        payment_viewset = PaymentViewSet()
        response = payment_viewset.earnings_summary(request)
        
        for emp in response.data.get('employees', []):
            if 'Yesther' in emp['employee_name']:
                print(f'Yesther - Pendiente: ${emp["pending_amount"]}, Sale IDs: {emp["pending_sale_ids"]}')

if __name__ == "__main__":
    test_period_logic()