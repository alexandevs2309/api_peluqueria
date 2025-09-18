#!/usr/bin/env python
"""
Script para verificar roles de usuario específico
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.auth_api.models import User
from apps.roles_api.models import Role, UserRole

def check_user_roles(email):
    """Verificar roles de un usuario específico"""
    
    try:
        user = User.objects.get(email=email)
        print(f"=== USUARIO: {user.email} ===")
        print(f"ID: {user.id}")
        print(f"Nombre: {user.full_name}")
        print(f"Activo: {user.is_active}")
        print(f"Superusuario: {user.is_superuser}")
        
        print(f"\n=== ROLES ASIGNADOS ===")
        user_roles = UserRole.objects.filter(user=user)
        
        if user_roles.exists():
            for user_role in user_roles:
                print(f"- {user_role.role.name} (scope: {user_role.role.scope})")
                print(f"  Tenant: {user_role.tenant or 'N/A'}")
                print(f"  Asignado: {user_role.assigned_at}")
                print(f"  Permisos del rol: {user_role.role.permissions.count()}")
        else:
            print("❌ No tiene roles asignados")
            
        print(f"\n=== ROLES DISPONIBLES ===")
        all_roles = Role.objects.all().order_by('name')
        for role in all_roles:
            print(f"- {role.name} (scope: {role.scope}, permisos: {role.permissions.count()})")
            
    except User.DoesNotExist:
        print(f"❌ Usuario {email} no encontrado")

if __name__ == '__main__':
    email = 'admin.aux@admin.com'
    check_user_roles(email)