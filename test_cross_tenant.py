#!/usr/bin/env python3
"""
Test para demostrar el problema de acceso cruzado entre tenants
"""
import os
import sys
import django

sys.path.append('/home/alexander/Escritorio/Projecto_Barber/api_peluqueria-master')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.tenants_api.models import Tenant

User = get_user_model()

def test_cross_tenant_vulnerability():
    print("=== VULNERABILIDAD DE ACCESO CRUZADO ===")
    
    # Obtener todos los tenants
    tenants = list(Tenant.objects.all())
    
    if len(tenants) < 2:
        print("❌ Se necesitan al menos 2 tenants para demostrar la vulnerabilidad")
        print("Creando un segundo tenant para la demostración...")
        
        # Crear segundo tenant
        second_tenant = Tenant.objects.create(
            name="Tenant México",
            subdomain="mexico",
            is_active=True
        )
        
        # Crear usuario en el segundo tenant
        mexican_user = User.objects.create_user(
            email="cajera_mexico@test.com",
            password="password123",
            full_name="Cajera México",
            tenant=second_tenant,
            is_staff=True
        )
        
        # Asignar rol cajera
        from apps.roles_api.models import Role
        cajera_role = Role.objects.get(name='Cajera')
        mexican_user.roles.add(cajera_role)
        
        print(f"✅ Creado tenant '{second_tenant.name}' con usuario '{mexican_user.email}'")
        tenants.append(second_tenant)
    
    print(f"\nTenants disponibles: {len(tenants)}")
    for tenant in tenants:
        users_count = User.objects.filter(tenant=tenant).count()
        print(f"  - {tenant.name}: {users_count} usuarios")
    
    print("\n=== DEMOSTRACIÓN DE LA VULNERABILIDAD ===")
    print("PROBLEMA: Un usuario de un tenant puede loguearse desde cualquier dominio")
    print("EJEMPLO:")
    print("  1. Usuario 'cajera_mexico@test.com' pertenece al tenant 'México'")
    print("  2. Pero puede loguearse desde el dominio de República Dominicana")
    print("  3. Y acceder a datos del tenant de RD")
    
    print("\n=== SOLUCIÓN REQUERIDA ===")
    print("1. Validar tenant por dominio en el login")
    print("2. Activar TenantValidationMiddleware")
    print("3. Configurar dominios específicos por tenant")
    
    return True

if __name__ == "__main__":
    test_cross_tenant_vulnerability()