#!/usr/bin/env python3
"""
Script para verificar que el flujo de registro corregido funciona correctamente
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.append('/home/alexander/Escritorio/clone/api_peluqueria-master')
django.setup()

from django.test import TestCase, TransactionTestCase
from django.db import transaction
from rest_framework.test import APIClient
from rest_framework import status
from apps.auth_api.models import User
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription
import json

def test_registration_flow():
    """Probar el flujo de registro completo"""
    print("🧪 INICIANDO PRUEBA DEL FLUJO DE REGISTRO CORREGIDO")
    print("=" * 60)
    
    # Limpiar datos de prueba
    User.objects.filter(email='test@example.com').delete()
    Tenant.objects.filter(name='Test Business').delete()
    
    # Crear plan de prueba si no existe
    plan, created = SubscriptionPlan.objects.get_or_create(
        name='basic',
        defaults={
            'description': 'Plan básico de prueba',
            'price': 29.99,
            'duration_month': 1,
            'max_employees': 5,
            'max_users': 10,
            'features': {'basic_features': True}
        }
    )
    print(f"✅ Plan de prueba: {'creado' if created else 'existente'}")
    
    # Datos de registro
    registration_data = {
        'fullName': 'Test User',
        'email': 'test@example.com',
        'businessName': 'Test Business',
        'planType': 'basic',
        'phone': '+1234567890',
        'address': 'Test Address 123'
    }
    
    # Simular request de registro
    client = APIClient()
    
    print("📤 Enviando solicitud de registro...")
    response = client.post('/api/subscriptions/register/', registration_data, format='json')
    
    print(f"📥 Respuesta HTTP: {response.status_code}")
    
    if response.status_code == 201:
        print("✅ REGISTRO EXITOSO")
        response_data = response.json()
        print(f"   - Usuario: {response_data['credentials']['email']}")
        print(f"   - Negocio: {response_data['account']['business_name']}")
        print(f"   - Plan: {response_data['account']['plan']}")
        
        # Verificar que el usuario fue creado
        try:
            user = User.objects.get(email='test@example.com')
            print(f"✅ Usuario creado: {user.email}")
            print(f"   - ID: {user.id}")
            print(f"   - Rol: {user.role}")
            print(f"   - Tenant: {user.tenant_id}")
            
            # Dar tiempo para que se ejecute transaction.on_commit
            import time
            time.sleep(1)
            
            # Refrescar usuario para ver cambios post-commit
            user.refresh_from_db()
            print(f"✅ Usuario después del commit:")
            print(f"   - Rol: {user.role}")
            print(f"   - Tenant ID: {user.tenant_id}")
            
            if user.tenant:
                print(f"✅ Tenant creado: {user.tenant.name}")
                print(f"   - Subdomain: {user.tenant.subdomain}")
                print(f"   - Plan: {user.tenant.plan_type}")
                print(f"   - Status: {user.tenant.subscription_status}")
                
                # Verificar suscripción
                subscription = UserSubscription.objects.filter(user=user).first()
                if subscription:
                    print(f"✅ Suscripción creada: {subscription.plan.name}")
                    print(f"   - Activa: {subscription.is_active}")
                    print(f"   - Fin: {subscription.end_date}")
                else:
                    print("❌ Suscripción no encontrada")
            else:
                print("⚠️ Tenant aún no asignado (puede estar procesándose)")
                
        except User.DoesNotExist:
            print("❌ Usuario no encontrado")
            
    else:
        print("❌ REGISTRO FALLÓ")
        try:
            error_data = response.json()
            print(f"   Error: {error_data}")
        except:
            print(f"   Error HTTP: {response.content}")
    
    print("=" * 60)
    print("🏁 PRUEBA COMPLETADA")

if __name__ == '__main__':
    test_registration_flow()