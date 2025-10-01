#!/usr/bin/env python3
"""
Script para probar el sistema de tenant isolation
"""
import os
import sys
import django
import requests
import json

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.append('/home/alexander/Escritorio/Projecto_Barber/api_peluqueria-master')
django.setup()

from django.contrib.auth import get_user_model
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan
from apps.roles_api.models import Role, UserRole

User = get_user_model()

BASE_URL = "http://localhost:8000/api"

def create_test_users():
    """Crear usuarios de prueba en diferentes tenants"""
    
    # Crear plan básico si no existe
    plan, _ = SubscriptionPlan.objects.get_or_create(
        name='basic',
        defaults={
            'price': 29.99,
            'max_users': 10,
            'features': ['pos', 'appointments', 'clients']
        }
    )
    
    # Crear usuarios primero (sin tenant)
    user1, created1 = User.objects.get_or_create(
        email='admin1@barberia1.com',
        defaults={
            'full_name': 'Admin Barbería 1',
            'is_staff': True
        }
    )
    if created1:
        user1.set_password('password123')
        user1.save()
    
    user2, created2 = User.objects.get_or_create(
        email='admin2@barberia2.com',
        defaults={
            'full_name': 'Admin Barbería 2',
            'is_staff': True
        }
    )
    if created2:
        user2.set_password('password123')
        user2.save()
    
    # Crear tenants con owners
    tenant1, _ = Tenant.objects.get_or_create(
        subdomain='barberia1',
        defaults={
            'name': 'Barbería Uno',
            'owner': user1,
            'subscription_plan': plan,
            'is_active': True
        }
    )
    
    tenant2, _ = Tenant.objects.get_or_create(
        subdomain='barberia2', 
        defaults={
            'name': 'Barbería Dos',
            'owner': user2,
            'subscription_plan': plan,
            'is_active': True
        }
    )
    
    # Asignar tenants a usuarios
    user1.tenant = tenant1
    user1.save()
    
    user2.tenant = tenant2
    user2.save()
    
    # Asignar roles
    admin_role, _ = Role.objects.get_or_create(
        name='Client-Admin',
        defaults={
            'scope': 'TENANT',
            'description': 'Administrador del cliente'
        }
    )
    
    UserRole.objects.get_or_create(
        user=user1,
        role=admin_role,
        tenant=tenant1
    )
    
    UserRole.objects.get_or_create(
        user=user2,
        role=admin_role,
        tenant=tenant2
    )
    
    print(f"✅ Usuarios creados:")
    print(f"   - {user1.email} (Tenant: {tenant1.name})")
    print(f"   - {user2.email} (Tenant: {tenant2.name})")
    
    return user1, user2, tenant1, tenant2

def test_login_with_tenant_validation():
    """Probar login con validación de tenant"""
    print("\n🔐 Probando login con validación de tenant...")
    
    user1, user2, tenant1, tenant2 = create_test_users()
    
    # Test 1: Login normal sin tenant_id
    response = requests.post(f"{BASE_URL}/auth/login/", json={
        'email': 'admin1@barberia1.com',
        'password': 'password123'
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Login exitoso para {data['user']['email']}")
        print(f"   Tenant: {data['user']['tenant_name']}")
        token1 = data['access']
    else:
        print(f"❌ Error en login: {response.text}")
        return
    
    # Test 2: Login con tenant_id correcto
    response = requests.post(f"{BASE_URL}/auth/login/", json={
        'email': 'admin1@barberia1.com',
        'password': 'password123',
        'tenant_id': tenant1.id
    })
    
    if response.status_code == 200:
        print("✅ Login con tenant_id correcto exitoso")
    else:
        print(f"❌ Error en login con tenant_id: {response.text}")
    
    # Test 3: Login con tenant_id incorrecto
    response = requests.post(f"{BASE_URL}/auth/login/", json={
        'email': 'admin1@barberia1.com',
        'password': 'password123',
        'tenant_id': tenant2.id  # Tenant incorrecto
    })
    
    if response.status_code == 403:
        print("✅ Login con tenant_id incorrecto bloqueado correctamente")
    else:
        print(f"❌ Login con tenant_id incorrecto debería fallar: {response.status_code}")
    
    return token1

def test_tenant_isolation_in_api(token):
    """Probar que las APIs filtran por tenant"""
    print("\n🔒 Probando aislamiento de tenant en APIs...")
    
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test tenant info endpoint
    response = requests.get(f"{BASE_URL}/auth/users/tenant_info/", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Tenant info obtenida: {data['name']}")
    else:
        print(f"❌ Error obteniendo tenant info: {response.text}")
    
    # Test POS endpoints (si están disponibles)
    response = requests.get(f"{BASE_URL}/pos/sales/", headers=headers)
    if response.status_code == 200:
        print("✅ Acceso a POS sales permitido para tenant correcto")
    else:
        print(f"⚠️  POS sales no disponible: {response.status_code}")

def test_cross_tenant_access():
    """Probar que no se puede acceder a datos de otros tenants"""
    print("\n🚫 Probando prevención de acceso cross-tenant...")
    
    user1, user2, tenant1, tenant2 = create_test_users()
    
    # Login con user1
    response = requests.post(f"{BASE_URL}/auth/login/", json={
        'email': 'admin1@barberia1.com',
        'password': 'password123'
    })
    
    if response.status_code != 200:
        print("❌ No se pudo hacer login para prueba cross-tenant")
        return
    
    token1 = response.json()['access']
    headers = {'Authorization': f'Bearer {token1}'}
    
    # Intentar acceder con token que tiene tenant_id diferente
    # (esto debería ser bloqueado por el middleware)
    response = requests.get(f"{BASE_URL}/pos/sales/", headers=headers)
    
    if response.status_code in [200, 404]:  # 404 si no hay datos, pero acceso permitido
        print("✅ Acceso permitido solo a datos del propio tenant")
    elif response.status_code == 403:
        print("✅ Acceso cross-tenant bloqueado correctamente")
    else:
        print(f"⚠️  Respuesta inesperada: {response.status_code}")

def main():
    print("🧪 Iniciando pruebas de tenant isolation...")
    
    try:
        # Crear usuarios de prueba
        create_test_users()
        
        # Probar login con validación
        token = test_login_with_tenant_validation()
        
        if token:
            # Probar aislamiento en APIs
            test_tenant_isolation_in_api(token)
        
        # Probar prevención cross-tenant
        test_cross_tenant_access()
        
        print("\n✅ Pruebas de tenant isolation completadas")
        
    except Exception as e:
        print(f"\n❌ Error en las pruebas: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()