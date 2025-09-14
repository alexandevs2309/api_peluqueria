#!/usr/bin/env python
"""
Script para crear los roles iniciales del sistema
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.roles_api.models import Role
from apps.auth_api.models import User

def create_initial_roles():
    """Crear los roles iniciales del sistema"""
    
    roles_to_create = [
        {
            'name': 'Super-Admin',
            'description': 'Administrador de la plataforma SaaS',
            'scope': 'GLOBAL'
        },
        {
            'name': 'Soporte',
            'description': 'Personal de soporte técnico (solo lectura)',
            'scope': 'GLOBAL'
        },
        {
            'name': 'Client-Admin',
            'description': 'Dueño de peluquería (administrador del tenant)',
            'scope': 'TENANT'
        },
        {
            'name': 'Manager',
            'description': 'Encargado de sucursal (sin configuración de tenant)',
            'scope': 'TENANT'
        },
        {
            'name': 'Client-Staff',
            'description': 'Empleado de peluquería (peluquero, manicurista, etc.)',
            'scope': 'TENANT'
        }
    ]
    
    print("=== CREANDO ROLES INICIALES ===")
    
    for role_data in roles_to_create:
        role, created = Role.objects.get_or_create(
            name=role_data['name'],
            defaults={
                'description': role_data['description'],
                'scope': role_data['scope']
            }
        )
        
        if created:
            print(f"✅ Creado: {role.name} (scope: {role.scope})")
        else:
            print(f"⚠️  Ya existe: {role.name} (scope: {role.scope})")
    
    print("\n=== ROLES EN BASE DE DATOS ===")
    roles = Role.objects.all().order_by('name')
    print(f"Total roles: {roles.count()}")
    for role in roles:
        print(f"- {role.name} (scope: {role.scope})")

def create_superuser():
    """Crear superusuario si no existe"""
    email = 'admin@admin.com'
    
    if not User.objects.filter(email=email).exists():
        print(f"\n=== CREANDO SUPERUSUARIO ===")
        user = User.objects.create_superuser(
            email=email,
            password='admin123',
            full_name='Alexander Del Rosario'
        )
        
        # Asignar rol Super-Admin
        super_admin_role = Role.objects.get(name='Super-Admin')
        user.roles.add(super_admin_role)
        
        print(f"✅ Superusuario creado: {email}")
        print(f"✅ Rol asignado: Super-Admin")
    else:
        print(f"\n⚠️  Superusuario ya existe: {email}")

if __name__ == '__main__':
    try:
        create_initial_roles()
        create_superuser()
        print("\n🎉 Inicialización completada!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)