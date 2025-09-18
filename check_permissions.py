#!/usr/bin/env python
"""
Script para verificar permisos disponibles en el sistema
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import Permission
from apps.roles_api.models import Role

def check_permissions():
    """Verificar permisos disponibles"""
    
    print("=== PERMISOS DE POS_API ===")
    pos_perms = Permission.objects.filter(content_type__app_label='pos_api').order_by('codename')
    for p in pos_perms:
        print(f"{p.id}: {p.codename} - {p.name}")
    
    print("\n=== PERMISOS DE BILLING_API ===")
    billing_perms = Permission.objects.filter(content_type__app_label='billing_api').order_by('codename')
    for p in billing_perms:
        print(f"{p.id}: {p.codename} - {p.name}")
    
    print("\n=== ROL CAJERA ===")
    try:
        cajera_role = Role.objects.get(name='Cajera')
        print(f"Rol: {cajera_role.name}")
        print(f"Descripción: {cajera_role.description}")
        print(f"Scope: {cajera_role.scope}")
        print(f"Permisos asignados: {cajera_role.permissions.count()}")
        
        print("\nPermisos del rol Cajera:")
        for perm in cajera_role.permissions.all().order_by('content_type__app_label', 'codename'):
            print(f"- {perm.content_type.app_label}.{perm.codename}: {perm.name}")
            
    except Role.DoesNotExist:
        print("❌ Rol Cajera no encontrado")

if __name__ == '__main__':
    check_permissions()