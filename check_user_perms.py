#!/usr/bin/env python3
import os
import sys
import django

sys.path.append('/home/alexander/Escritorio/Projecto_Barber/api_peluqueria-master')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.roles_api.models import Role

User = get_user_model()

def check_user_by_email(email):
    try:
        user = User.objects.get(email=email)
        print(f"Usuario: {user.email}")
        print(f"ID: {user.id}")
        print(f"is_staff: {user.is_staff}")
        print(f"is_active: {user.is_active}")
        print(f"tenant: {user.tenant}")
        print(f"Roles: {[r.name for r in user.roles.all()]}")
        
        # Verificar permisos específicos del frontend
        roles = [r.name for r in user.roles.all()]
        print(f"\nVerificación de roles del frontend:")
        print(f"isClientAdmin(): {'Client-Admin' in roles}")
        print(f"isCashier(): {'Cajera' in roles}")
        print(f"isStylist(): {'Client-Staff' in roles}")
        print(f"isGlobalRole(): {'Super-Admin' in roles or 'Soporte' in roles}")
        
        # Simular canProcessSales()
        can_process = 'Client-Admin' in roles or 'Cajera' in roles
        print(f"canProcessSales(): {can_process}")
        
        return user
    except User.DoesNotExist:
        print(f"Usuario {email} no encontrado")
        return None

if __name__ == "__main__":
    print("Ingresa el email del usuario cajera:")
    email = input().strip()
    check_user_by_email(email)