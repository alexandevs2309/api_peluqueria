#!/usr/bin/env python3
"""
Test para verificar que el filtrado por tenant funciona correctamente
"""
import os
import sys
import django

sys.path.append('/home/alexander/Escritorio/Projecto_Barber/api_peluqueria-master')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.pos_api.models import CashRegister, Sale
from apps.tenants_api.models import Tenant

User = get_user_model()

def test_tenant_isolation():
    print("=== TEST: AISLAMIENTO POR TENANT ===")
    
    # Obtener todos los tenants
    tenants = Tenant.objects.all()
    print(f"Total tenants: {tenants.count()}")
    
    for tenant in tenants:
        print(f"\n--- Tenant: {tenant.name} (ID: {tenant.id}) ---")
        
        # Usuarios en este tenant
        users = User.objects.filter(tenant=tenant)
        print(f"Usuarios: {users.count()}")
        
        for user in users[:2]:  # Solo mostrar los primeros 2
            print(f"  - {user.email} (Roles: {[r.name for r in user.roles.all()]})")
        
        # Cajas registradoras en este tenant
        registers = CashRegister.objects.filter(user__tenant=tenant)
        print(f"Cajas registradoras: {registers.count()}")
        
        # Ventas en este tenant
        sales = Sale.objects.filter(user__tenant=tenant)
        print(f"Ventas: {sales.count()}")

def test_cross_tenant_access():
    print("\n=== TEST: ACCESO CRUZADO ENTRE TENANTS ===")
    
    # Obtener usuarios de diferentes tenants
    tenants = list(Tenant.objects.all()[:2])  # Primeros 2 tenants
    
    if len(tenants) < 2:
        print("❌ Se necesitan al menos 2 tenants para este test")
        return
    
    tenant1, tenant2 = tenants[0], tenants[1]
    
    user1 = User.objects.filter(tenant=tenant1).first()
    user2 = User.objects.filter(tenant=tenant2).first()
    
    if not user1 or not user2:
        print("❌ No se encontraron usuarios en ambos tenants")
        return
    
    print(f"Usuario 1: {user1.email} (Tenant: {tenant1.name})")
    print(f"Usuario 2: {user2.email} (Tenant: {tenant2.name})")
    
    # Verificar que cada usuario solo ve sus propias cajas
    user1_registers = CashRegister.objects.filter(user__tenant=user1.tenant)
    user2_registers = CashRegister.objects.filter(user__tenant=user2.tenant)
    
    print(f"\nCajas visibles para {user1.email}: {user1_registers.count()}")
    print(f"Cajas visibles para {user2.email}: {user2_registers.count()}")
    
    # Verificar que no hay solapamiento
    overlap = user1_registers.filter(user__tenant=user2.tenant).count()
    print(f"Solapamiento (debe ser 0): {overlap}")
    
    if overlap == 0:
        print("✅ Aislamiento por tenant funcionando correctamente")
    else:
        print("❌ PROBLEMA: Hay acceso cruzado entre tenants")

if __name__ == "__main__":
    test_tenant_isolation()
    test_cross_tenant_access()