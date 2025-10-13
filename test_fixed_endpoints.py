#!/usr/bin/env python
import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# Login
login_data = {"email": "admin@admin.com", "password": "superadmin123"}
response = requests.post('http://localhost:8000/api/auth/login/', json=login_data)
token = response.json()['access']
headers = {'Authorization': f'Bearer {token}'}

print("=== PROBANDO ENDPOINTS ARREGLADOS ===")

# Probar endpoints que fallaron
endpoints = [
    'http://localhost:8000/api/tenants/admin/users/',
    'http://localhost:8000/api/tenants/admin/users/stats/',
]

for url in endpoints:
    try:
        response = requests.get(url, headers=headers)
        print(f"GET {url}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS")
            data = response.json()
            if isinstance(data, dict):
                print(f"Keys: {list(data.keys())}")
            elif isinstance(data, list):
                print(f"Items: {len(data)}")
        else:
            print("❌ ERROR")
            print(f"Error: {response.text[:200]}...")
        print("-" * 50)
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        print("-" * 50)

print("=== PROBANDO FUNCIONALIDADES ADICIONALES ===")

# Probar marcar factura como pagada
try:
    invoices_response = requests.get('http://localhost:8000/api/billing/invoices/', headers=headers)
    if invoices_response.status_code == 200:
        invoices = invoices_response.json()['results']
        unpaid_invoice = next((inv for inv in invoices if not inv['is_paid']), None)
        
        if unpaid_invoice:
            pay_response = requests.post(
                f"http://localhost:8000/api/billing/invoices/{unpaid_invoice['id']}/mark_as_paid/",
                headers=headers
            )
            print(f"Marcar factura #{unpaid_invoice['id']} como pagada:")
            print(f"Status: {pay_response.status_code}")
            if pay_response.status_code == 200:
                print("✅ SUCCESS")
                print(f"Response: {pay_response.json()}")
            else:
                print("❌ ERROR")
                print(f"Error: {pay_response.text}")
        else:
            print("No hay facturas sin pagar para probar")
except Exception as e:
    print(f"Error probando pago: {str(e)}")

print("=" * 50)
print("PRUEBAS COMPLETADAS")