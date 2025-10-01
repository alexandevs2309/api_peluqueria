#!/usr/bin/env python3
"""
Script para debuggear problemas del POS
"""
import os
import sys
import django

# Configurar Django
sys.path.append('/home/alexander/Escritorio/Projecto_Barber/api_peluqueria-master')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.roles_api.models import Role
from apps.pos_api.models import CashRegister

User = get_user_model()

def check_cashier_permissions():
    print("=== VERIFICACIÓN DE PERMISOS CAJERA ===")
    
    # Buscar usuarios con rol Cajera
    cajera_role = Role.objects.filter(name='Cajera').first()
    if not cajera_role:
        print("❌ No se encontró el rol 'Cajera'")
        return
    
    cajeras = User.objects.filter(roles=cajera_role)
    print(f"✅ Rol Cajera encontrado. Usuarios con este rol: {cajeras.count()}")
    
    for cajera in cajeras:
        print(f"\n--- Usuario: {cajera.email} ---")
        print(f"ID: {cajera.id}")
        print(f"is_staff: {cajera.is_staff}")
        print(f"is_active: {cajera.is_active}")
        print(f"Roles: {[r.name for r in cajera.roles.all()]}")
        
        # Verificar permisos específicos
        perms = [
            'pos_api.add_sale',
            'pos_api.view_sale', 
            'pos_api.add_cashregister',
            'pos_api.view_cashregister'
        ]
        
        print("Permisos:")
        for perm in perms:
            has_perm = cajera.has_perm(perm)
            print(f"  {perm}: {'✅' if has_perm else '❌'}")

def check_cash_registers():
    print("\n=== VERIFICACIÓN DE CAJAS REGISTRADORAS ===")
    
    registers = CashRegister.objects.all().order_by('-opened_at')[:5]
    print(f"Total de cajas registradoras: {CashRegister.objects.count()}")
    print("Últimas 5 cajas:")
    
    for reg in registers:
        print(f"  ID: {reg.id} | Usuario: {reg.user.email} | Abierta: {reg.is_open} | Fecha: {reg.opened_at}")

def check_roles():
    print("\n=== VERIFICACIÓN DE ROLES ===")
    
    roles = Role.objects.all()
    for role in roles:
        users_with_role = User.objects.filter(roles=role)
        users_count = users_with_role.count()
        print(f"Rol: {role.name} | Usuarios: {users_count}")
        if users_count > 0:
            users = users_with_role[:3]  # Mostrar solo los primeros 3
            for user in users:
                print(f"  - {user.email} (is_staff: {user.is_staff})")

if __name__ == "__main__":
    check_roles()
    check_cashier_permissions()
    check_cash_registers()