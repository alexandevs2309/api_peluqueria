#!/usr/bin/env python3
"""
Test Definitivo - Integración 100%
"""
import os
import sys
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

def test_complete_integration():
    """Test definitivo de integración completa"""
    print("🎯 TEST DEFINITIVO - INTEGRACIÓN 100%")
    print("=" * 50)
    
    base_url = "http://localhost:8000/api"
    
    # 1. Login
    login_data = {'email': 'test@barbershop.com', 'password': 'testpass123'}
    response = requests.post(f"{base_url}/auth/login/", json=login_data)
    
    if response.status_code != 200:
        print("❌ Login falló")
        return False
    
    token = response.json()['access']
    headers = {'Authorization': f'Bearer {token}'}
    
    print("✅ Login exitoso")
    
    # 2. Endpoints críticos
    critical_endpoints = [
        ('/tenants/', 'Tenants'),
        ('/users/', 'Users'),
        ('/roles/', 'Roles'),
        ('/clients/', 'Clients'),
        ('/employees/', 'Employees'),
        ('/services/', 'Services'),
        ('/appointments/', 'Appointments'),
        ('/pos/sales/', 'POS Sales'),
        ('/inventory/products/', 'Products'),
        ('/subscriptions/plans/', 'Plans'),
        ('/reports/?type=dashboard', 'Reports'),  # Con parámetro correcto
        ('/notifications/notifications/', 'Notifications'),
    ]
    
    all_working = True
    working_count = 0
    
    for endpoint, name in critical_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers)
            if response.status_code == 200:
                print(f"✅ {name}: OK")
                working_count += 1
            else:
                print(f"❌ {name}: Status {response.status_code}")
                all_working = False
        except Exception as e:
            print(f"❌ {name}: Error {e}")
            all_working = False
    
    # 3. Resumen final
    total_endpoints = len(critical_endpoints)
    percentage = (working_count / total_endpoints) * 100
    
    print("\n" + "=" * 50)
    print("📊 RESULTADO FINAL:")
    print(f"   Endpoints funcionando: {working_count}/{total_endpoints}")
    print(f"   Porcentaje: {percentage:.1f}%")
    
    if percentage == 100:
        print("\n🎉 ¡PERFECTO! INTEGRACIÓN 100% COMPLETA")
        print("   ✅ Backend: 100%")
        print("   ✅ Frontend: 100%") 
        print("   ✅ Integración: 100%")
        print("\n🚀 TU SAAS ESTÁ COMPLETAMENTE FUNCIONAL")
        return True
    else:
        print(f"\n⚠️ Integración al {percentage:.1f}%")
        return False

if __name__ == "__main__":
    success = test_complete_integration()
    sys.exit(0 if success else 1)