#!/usr/bin/env python3
"""
Script de verificación completa del sistema
Ejecutar: python verify_system.py
"""
import os
import sys
import django
import requests
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from apps.roles_api.models import Role, UserRole
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan
from apps.payments_api.models import PaymentProvider

User = get_user_model()

def test_database():
    """Verificar conexión a base de datos"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✅ Base de datos: Conectada")
        return True
    except Exception as e:
        print(f"❌ Base de datos: Error - {e}")
        return False

def test_cache():
    """Verificar Redis cache"""
    try:
        cache.set('test_key', 'test_value', 30)
        value = cache.get('test_key')
        if value == 'test_value':
            print("✅ Redis Cache: Funcionando")
            return True
        else:
            print("❌ Redis Cache: No funciona")
            return False
    except Exception as e:
        print(f"❌ Redis Cache: Error - {e}")
        return False

def test_roles():
    """Verificar sistema de roles"""
    try:
        roles = Role.objects.all()
        if roles.exists():
            print(f"✅ Roles: {roles.count()} roles configurados")
            for role in roles:
                print(f"   - {role.name}")
            return True
        else:
            print("⚠️ Roles: No hay roles configurados")
            return False
    except Exception as e:
        print(f"❌ Roles: Error - {e}")
        return False

def test_superuser():
    """Verificar superusuario"""
    try:
        superusers = User.objects.filter(is_superuser=True)
        if superusers.exists():
            print(f"✅ Superuser: {superusers.count()} superusuarios")
            return True
        else:
            print("⚠️ Superuser: No hay superusuarios")
            return False
    except Exception as e:
        print(f"❌ Superuser: Error - {e}")
        return False

def test_tenants():
    """Verificar sistema multitenancy"""
    try:
        tenants = Tenant.objects.all()
        print(f"✅ Tenants: {tenants.count()} tenants configurados")
        return True
    except Exception as e:
        print(f"❌ Tenants: Error - {e}")
        return False

def test_subscription_plans():
    """Verificar planes de suscripción"""
    try:
        plans = SubscriptionPlan.objects.all()
        if plans.exists():
            print(f"✅ Planes: {plans.count()} planes configurados")
            for plan in plans:
                print(f"   - {plan.name}: ${plan.price}")
            return True
        else:
            print("⚠️ Planes: No hay planes configurados")
            return False
    except Exception as e:
        print(f"❌ Planes: Error - {e}")
        return False

def test_payment_providers():
    """Verificar proveedores de pago"""
    try:
        providers = PaymentProvider.objects.all()
        if providers.exists():
            print(f"✅ Pagos: {providers.count()} proveedores configurados")
            for provider in providers:
                status = "Activo" if provider.is_active else "Inactivo"
                print(f"   - {provider.name}: {status}")
            return True
        else:
            print("⚠️ Pagos: No hay proveedores configurados")
            return False
    except Exception as e:
        print(f"❌ Pagos: Error - {e}")
        return False

def test_endpoints():
    """Verificar endpoints principales"""
    base_url = "http://localhost:8000"
    endpoints = [
        ("/api/healthz/", "Healthcheck"),
        ("/api/docs/", "API Docs"),
        ("/api/schema/", "API Schema"),
        ("/admin/", "Django Admin"),
    ]
    
    results = []
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: Status {response.status_code}")
                results.append(True)
            else:
                print(f"⚠️ {name}: Status {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ {name}: Error - {e}")
            results.append(False)
    
    return all(results)

def test_security_settings():
    """Verificar configuraciones de seguridad"""
    checks = []
    
    # JWT
    if hasattr(settings, 'SIMPLE_JWT'):
        print("✅ JWT: Configurado")
        checks.append(True)
    else:
        print("❌ JWT: No configurado")
        checks.append(False)
    
    # CORS
    if hasattr(settings, 'CORS_ALLOWED_ORIGINS'):
        print("✅ CORS: Configurado")
        checks.append(True)
    else:
        print("❌ CORS: No configurado")
        checks.append(False)
    
    # Sentry
    if hasattr(settings, 'SENTRY_DSN'):
        print("✅ Sentry: Configurado")
        checks.append(True)
    else:
        print("❌ Sentry: No configurado")
        checks.append(False)
    
    # HTTPS Settings
    if not settings.DEBUG:
        if settings.SECURE_SSL_REDIRECT:
            print("✅ HTTPS: Configurado para producción")
            checks.append(True)
        else:
            print("⚠️ HTTPS: No forzado en producción")
            checks.append(False)
    else:
        print("ℹ️ HTTPS: Modo desarrollo (OK)")
        checks.append(True)
    
    return all(checks)

def main():
    print("🔍 VERIFICACIÓN COMPLETA DEL SISTEMA")
    print("=" * 50)
    
    tests = [
        ("Base de Datos", test_database),
        ("Cache Redis", test_cache),
        ("Sistema de Roles", test_roles),
        ("Superusuario", test_superuser),
        ("Multitenancy", test_tenants),
        ("Planes de Suscripción", test_subscription_plans),
        ("Proveedores de Pago", test_payment_providers),
        ("Endpoints API", test_endpoints),
        ("Configuración de Seguridad", test_security_settings),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Error en {test_name}: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 RESUMEN FINAL:")
    
    passed = sum(results)
    total = len(results)
    percentage = (passed / total) * 100
    
    if percentage == 100:
        print(f"🎉 PERFECTO: {passed}/{total} pruebas pasaron ({percentage:.0f}%)")
        print("✅ Sistema completamente configurado y funcionando")
    elif percentage >= 80:
        print(f"✅ BUENO: {passed}/{total} pruebas pasaron ({percentage:.0f}%)")
        print("⚠️ Algunas configuraciones menores pendientes")
    else:
        print(f"⚠️ NECESITA ATENCIÓN: {passed}/{total} pruebas pasaron ({percentage:.0f}%)")
        print("❌ Configuraciones importantes pendientes")
    
    return percentage == 100

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)