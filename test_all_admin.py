#!/usr/bin/env python
import os
import django
import requests
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

def test_endpoint(method, url, headers, data=None):
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        
        print(f"{method} {url}")
        print(f"Status: {response.status_code}")
        
        if response.status_code < 400:
            print("✅ SUCCESS")
            if response.text:
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        print(f"Keys: {list(data.keys())}")
                    elif isinstance(data, list):
                        print(f"Items: {len(data)}")
                except:
                    print(f"Response: {response.text[:100]}...")
        else:
            print("❌ ERROR")
            print(f"Error: {response.text}")
        print("-" * 50)
        return response
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        print("-" * 50)
        return None

# Login para obtener token
print("=== OBTENIENDO TOKEN SUPERADMIN ===")
login_data = {"email": "admin@admin.com", "password": "superadmin123"}
response = requests.post('http://localhost:8000/api/auth/login/', json=login_data)

if response.status_code != 200:
    print(f"❌ LOGIN FAILED: {response.text}")
    exit(1)

token = response.json()['access']
headers = {'Authorization': f'Bearer {token}'}
print("✅ Token obtenido")
print("=" * 50)

# ENDPOINTS SUPERADMIN A PROBAR
endpoints = [
    # Métricas SaaS
    ('GET', 'http://localhost:8000/api/settings/admin/metrics/'),
    
    # Monitoreo del sistema
    ('GET', 'http://localhost:8000/api/settings/admin/system-monitor/'),
    
    # Test de servicios
    ('POST', 'http://localhost:8000/api/settings/admin/test-service/', {'service': 'email'}),
    ('POST', 'http://localhost:8000/api/settings/admin/test-service/', {'service': 'payments'}),
    ('POST', 'http://localhost:8000/api/settings/admin/test-service/', {'service': 'paypal'}),
    ('POST', 'http://localhost:8000/api/settings/admin/test-service/', {'service': 'twilio'}),
    
    # Reportes SuperAdmin
    ('GET', 'http://localhost:8000/api/reports/admin/'),
    ('GET', 'http://localhost:8000/api/reports/admin/?period=last_7_days'),
    
    # Gestión de usuarios SuperAdmin
    ('GET', 'http://localhost:8000/api/tenants/admin/users/'),
    ('GET', 'http://localhost:8000/api/tenants/admin/users/stats/'),
    ('GET', 'http://localhost:8000/api/tenants/admin/users/available_roles/'),
    ('GET', 'http://localhost:8000/api/tenants/admin/users/available_tenants/'),
    
    # Estadísticas de facturación
    ('GET', 'http://localhost:8000/api/billing/admin/stats/'),
    
    # Endpoints básicos existentes
    ('GET', 'http://localhost:8000/api/tenants/'),
    ('GET', 'http://localhost:8000/api/subscriptions/plans/'),
    ('GET', 'http://localhost:8000/api/billing/invoices/'),
    ('GET', 'http://localhost:8000/api/audit/logs/'),
    
    # Configuración del sistema
    ('GET', 'http://localhost:8000/api/system-settings/'),
    ('GET', 'http://localhost:8000/api/settings/integrations/status/'),
]

print("=== PROBANDO TODOS LOS ENDPOINTS SUPERADMIN ===")
success_count = 0
error_count = 0

for endpoint in endpoints:
    method = endpoint[0]
    url = endpoint[1]
    data = endpoint[2] if len(endpoint) > 2 else None
    
    response = test_endpoint(method, url, headers, data)
    
    if response and response.status_code < 400:
        success_count += 1
    else:
        error_count += 1

print("=" * 50)
print(f"RESUMEN FINAL:")
print(f"✅ Exitosos: {success_count}")
print(f"❌ Errores: {error_count}")
print(f"📊 Total: {success_count + error_count}")

if error_count == 0:
    print("🎉 TODOS LOS ENDPOINTS FUNCIONAN CORRECTAMENTE!")
else:
    print(f"⚠️  HAY {error_count} ENDPOINTS CON PROBLEMAS")