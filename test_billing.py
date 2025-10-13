#!/usr/bin/env python
import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# Login para obtener token
login_data = {
    "email": "admin@admin.com",
    "password": "superadmin123"
}

response = requests.post('http://localhost:8000/api/auth/login/', json=login_data)
if response.status_code == 200:
    token = response.json()['access']
    print(f"Token obtenido: {token[:50]}...")
    
    # Probar endpoint de facturas
    headers = {'Authorization': f'Bearer {token}'}
    
    # Ver facturas
    invoices_response = requests.get('http://localhost:8000/api/billing/invoices/', headers=headers)
    if invoices_response.status_code == 200:
        invoices = invoices_response.json()['results']
        print(f"\nFacturas encontradas: {len(invoices)}")
        
        # Mostrar primera factura
        if invoices:
            invoice = invoices[0]
            print(f"Factura #{invoice['id']}:")
            print(f"  Usuario: {invoice['user_email']}")
            print(f"  Tenant: {invoice['tenant_name']}")
            print(f"  Plan: {invoice['plan_name']}")
            print(f"  Monto: ${invoice['amount']}")
            print(f"  Pagada: {invoice['is_paid']}")
            
            # Probar pago si no está pagada
            if not invoice['is_paid']:
                pay_response = requests.post(
                    f"http://localhost:8000/api/billing/invoices/{invoice['id']}/pay/",
                    headers=headers
                )
                print(f"\nPago - Status: {pay_response.status_code}")
                print(f"Respuesta: {pay_response.text}")
    else:
        print(f"Error al obtener facturas: {invoices_response.status_code}")
        print(invoices_response.text)
else:
    print(f"Error en login: {response.status_code}")
    print(response.text)