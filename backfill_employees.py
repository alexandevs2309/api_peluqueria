#!/usr/bin/env python3
"""
Script de backfill para crear Employee records faltantes.
Garantiza integridad User-Employee para datos existentes.
"""

import os
import sys
import django

# Setup Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.auth_api.models import User
from apps.employees_api.models import Employee
from django.db import transaction

# Roles que requieren Employee
EMPLOYEE_ROLES = ['Estilista', 'Cajera', 'Manager', 'Utility']

def backfill_missing_employees():
    """Crear Employee records para Users empleados que no los tienen"""
    
    print("=== BACKFILL: CREANDO EMPLOYEE RECORDS FALTANTES ===")
    
    # Encontrar Users empleados sin Employee
    users_without_employee = User.objects.filter(
        role__in=EMPLOYEE_ROLES
    ).exclude(
        id__in=Employee.objects.values_list('user_id', flat=True)
    )
    
    print(f"Users empleados sin Employee encontrados: {users_without_employee.count()}")
    
    created_count = 0
    errors = []
    
    for user in users_without_employee:
        try:
            with transaction.atomic():
                if not user.tenant:
                    errors.append(f"User {user.id} ({user.email}) sin tenant - OMITIDO")
                    continue
                
                employee, created = Employee.objects.get_or_create(
                    user=user,
                    defaults={
                        'tenant': user.tenant,
                        'is_active': True,
                        'specialty': '',
                        'phone': '',
                    }
                )
                
                if created:
                    created_count += 1
                    print(f"✅ Employee creado para User {user.id} ({user.email}) en tenant {user.tenant}")
                else:
                    print(f"⚠️  Employee ya existía para User {user.id} ({user.email})")
                    
        except Exception as e:
            error_msg = f"❌ Error creando Employee para User {user.id} ({user.email}): {str(e)}"
            errors.append(error_msg)
            print(error_msg)
    
    print(f"\n=== RESUMEN BACKFILL ===")
    print(f"Employee records creados: {created_count}")
    print(f"Errores: {len(errors)}")
    
    if errors:
        print("\n=== ERRORES DETALLADOS ===")
        for error in errors:
            print(error)
    
    return created_count, errors

def verify_integrity():
    """Verificar integridad User-Employee después del backfill"""
    
    print("\n=== VERIFICACIÓN DE INTEGRIDAD ===")
    
    # Contar Users empleados
    employee_users = User.objects.filter(role__in=EMPLOYEE_ROLES)
    print(f"Total Users con rol empleado: {employee_users.count()}")
    
    # Contar Employee records
    employees = Employee.objects.all()
    print(f"Total Employee records: {employees.count()}")
    
    # Verificar Users sin Employee
    users_without_employee = employee_users.exclude(
        id__in=employees.values_list('user_id', flat=True)
    )
    
    if users_without_employee.exists():
        print(f"❌ FALTA INTEGRIDAD: {users_without_employee.count()} Users empleados sin Employee")
        for user in users_without_employee:
            print(f"   - User {user.id} ({user.email}) - Tenant: {user.tenant}")
        return False
    else:
        print("✅ INTEGRIDAD GARANTIZADA: Todos los Users empleados tienen Employee")
        return True

if __name__ == "__main__":
    print("Iniciando backfill de Employee records...")
    
    # Ejecutar backfill
    created, errors = backfill_missing_employees()
    
    # Verificar integridad
    integrity_ok = verify_integrity()
    
    if integrity_ok and len(errors) == 0:
        print("\n🎉 BACKFILL COMPLETADO EXITOSAMENTE")
        print("✅ Integridad User-Employee garantizada")
    else:
        print("\n⚠️  BACKFILL COMPLETADO CON ADVERTENCIAS")
        if not integrity_ok:
            print("❌ Integridad no completamente garantizada")
        if errors:
            print(f"❌ {len(errors)} errores durante el proceso")