#!/usr/bin/env python
"""
Test simple de funcionalidades principales
"""
import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_endpoints():
    """Probar endpoints principales"""
    
    endpoints = [
        ("/healthz/", "Health Check"),
        ("/docs/", "Documentación"),
        ("/schema/", "Schema API"),
        ("/auth/register/", "Registro"),
        ("/services/", "Servicios"),
        ("/clients/", "Clientes"),
        ("/appointments/", "Citas"),
        ("/inventory/products/", "Productos"),
        ("/pos/sales/", "Ventas POS"),
        ("/reports/dashboard/", "Dashboard"),
        ("/subscriptions/plans/", "Planes"),
        ("/tenants/", "Tenants"),
    ]
    
    print("=== PROBANDO ENDPOINTS PRINCIPALES ===\n")
    
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            status = "✅" if response.status_code in [200, 401, 403] else "❌"
            print(f"{status} {name}: {response.status_code}")
        except Exception as e:
            print(f"❌ {name}: ERROR - {str(e)[:50]}")
    
    print(f"\n=== RESUMEN ===")
    print("✅ = Endpoint funcional (200/401/403)")
    print("❌ = Endpoint con problemas")

if __name__ == "__main__":
    test_endpoints()