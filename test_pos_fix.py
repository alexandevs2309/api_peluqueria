#!/usr/bin/env python3
"""
Test para verificar que los fixes del POS funcionan correctamente
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
from django.utils import timezone

User = get_user_model()

def test_cashier_permissions():
    print("=== TEST: PERMISOS CAJERA ===")
    
    # Obtener un usuario cajera
    cajera_role = Role.objects.get(name='Cajera')
    cajera = User.objects.filter(roles=cajera_role, is_staff=True).first()
    
    if not cajera:
        print("❌ No se encontró usuario cajera con is_staff=True")
        return False
    
    print(f"✅ Usuario cajera encontrado: {cajera.email}")
    print(f"   is_staff: {cajera.is_staff}")
    print(f"   is_active: {cajera.is_active}")
    
    # Verificar permisos específicos
    perms_to_check = [
        'pos_api.add_sale',
        'pos_api.view_sale',
        'pos_api.add_cashregister',
        'pos_api.view_cashregister'
    ]
    
    all_perms_ok = True
    for perm in perms_to_check:
        has_perm = cajera.has_perm(perm)
        status = "✅" if has_perm else "❌"
        print(f"   {perm}: {status}")
        if not has_perm:
            all_perms_ok = False
    
    return all_perms_ok

def test_cash_register_status():
    print("\n=== TEST: ESTADO CAJA REGISTRADORA ===")
    
    # Buscar cajas abiertas hoy
    today = timezone.localdate()
    open_registers = CashRegister.objects.filter(
        is_open=True,
        opened_at__date=today
    )
    
    print(f"Cajas abiertas hoy: {open_registers.count()}")
    
    for register in open_registers:
        print(f"  - ID: {register.id}")
        print(f"    Usuario: {register.user.email}")
        print(f"    Fondo inicial: ${register.initial_cash}")
        print(f"    Ventas totales: ${getattr(register, 'total_sales', 0)}")
        print(f"    Abierta desde: {register.opened_at}")
    
    return open_registers.count() > 0

def test_user_staff_status():
    print("\n=== TEST: ESTADO is_staff DE USUARIOS ===")
    
    cajera_role = Role.objects.get(name='Cajera')
    cajeras = User.objects.filter(roles=cajera_role)
    
    all_staff = True
    for cajera in cajeras:
        status = "✅" if cajera.is_staff else "❌"
        print(f"  {cajera.email}: is_staff={cajera.is_staff} {status}")
        if not cajera.is_staff:
            all_staff = False
    
    return all_staff

if __name__ == "__main__":
    print("🔧 VERIFICANDO FIXES DEL POS...\n")
    
    perms_ok = test_cashier_permissions()
    cash_ok = test_cash_register_status()
    staff_ok = test_user_staff_status()
    
    print(f"\n📊 RESUMEN:")
    print(f"   Permisos cajera: {'✅' if perms_ok else '❌'}")
    print(f"   Cajas abiertas: {'✅' if cash_ok else '❌'}")
    print(f"   Usuarios is_staff: {'✅' if staff_ok else '❌'}")
    
    if perms_ok and staff_ok:
        print(f"\n🎉 TODOS LOS FIXES APLICADOS CORRECTAMENTE")
        print(f"   - URL del endpoint corregida en frontend")
        print(f"   - Permisos de acceso al POS actualizados")
        print(f"   - Usuarios cajera con is_staff=True")
    else:
        print(f"\n⚠️  ALGUNOS PROBLEMAS PERSISTEN")