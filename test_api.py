#!/usr/bin/env python
"""
Script para probar las funcionalidades principales de la API
"""
import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_health():
    """Probar health check"""
    response = requests.get(f"{BASE_URL}/healthz/")
    print(f"Health Check: {response.status_code} - {response.json()}")
    return response.status_code == 200

def test_register():
    """Probar registro de usuario"""
    data = {
        "email": "test@peluqueria.com",
        "password": "TestPass123!",
        "password2": "TestPass123!",
        "full_name": "Usuario Test",
        "phone": "1234567890",
        "role": "Client"
    }
    response = requests.post(f"{BASE_URL}/auth/register/", json=data)
    print(f"Registro: {response.status_code} - {response.text[:200]}")
    return response.status_code in [200, 201]

def test_login():
    """Probar login"""
    data = {
        "email": "test@peluqueria.com",
        "password": "TestPass123!"
    }
    response = requests.post(f"{BASE_URL}/auth/login/", json=data)
    print(f"Login: {response.status_code} - {response.text[:200]}")
    if response.status_code == 200:
        return response.json().get('access')
    return None

def test_protected_endpoint(token):
    """Probar endpoint protegido"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/reports/dashboard/", headers=headers)
    print(f"Dashboard: {response.status_code} - {response.text[:200]}")
    return response.status_code == 200

if __name__ == "__main__":
    print("=== PROBANDO API PELUQUERÍA ===")
    
    # 1. Health Check
    if test_health():
        print("✅ Health Check OK")
    else:
        print("❌ Health Check FAIL")
    
    # 2. Registro
    if test_register():
        print("✅ Registro OK")
    else:
        print("❌ Registro FAIL")
    
    # 3. Login
    token = test_login()
    if token:
        print("✅ Login OK")
        
        # 4. Endpoint protegido
        if test_protected_endpoint(token):
            print("✅ Dashboard OK")
        else:
            print("❌ Dashboard FAIL")
    else:
        print("❌ Login FAIL")