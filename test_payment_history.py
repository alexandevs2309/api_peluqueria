#!/usr/bin/env python
"""
Probar historial de pagos
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import RequestFactory
from apps.employees_api.payments_views import PaymentViewSet
from apps.auth_api.models import User

def test_payment_history():
    # Simular request
    factory = RequestFactory()
    request = factory.get('/api/employees/payments/payment_history/')
    user = User.objects.filter(email='alexanderdelrosarioperez@gmail.com').first()
    request.user = user

    # Llamar al endpoint
    viewset = PaymentViewSet()
    response = viewset.payment_history(request)

    print('=== HISTORIAL DE PAGOS ===')
    print(f'Status: {response.status_code}')
    if hasattr(response, 'data'):
        data = response.data
        print(f'Total pagos: {len(data.get("payments", []))}')
        for payment in data.get('payments', []):
            print(f'- {payment["employee"]["name"]}: ${payment["amounts"]["net_amount"]} ({payment["period"]["display"]})')
            print(f'  Recibo: {payment["receipt"]["number"]}')
            print(f'  Pagado: {payment["payment_details"]["paid_at"]}')
            print(f'  Ventas: {len(payment["sales"])} ventas')
            print()

if __name__ == "__main__":
    test_payment_history()