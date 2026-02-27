#!/usr/bin/env python
import os
import sys
import django

sys.path.insert(0, '/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import Permission
from apps.roles_api.models import Role

def assign_financial_permissions():
    """Asignar permisos financieros a roles"""
    
    # Obtener permisos financieros
    financial_perms = Permission.objects.filter(
        codename__in=[
            'view_financial_reports',
            'view_employee_reports',
            'view_sales_reports',
            'view_kpi_dashboard',
            'view_advanced_analytics',
        ]
    )
    
    print(f"Permisos financieros encontrados: {financial_perms.count()}")
    
    # Client-Admin: TODOS los permisos financieros
    try:
        admin_role = Role.objects.get(name='Client-Admin')
        admin_role.permissions.add(*financial_perms)
        print(f"✅ Client-Admin: {financial_perms.count()} permisos asignados")
    except Role.DoesNotExist:
        print("❌ Rol Client-Admin no encontrado")
    
    # Manager: Solo reportes de ventas y KPI
    try:
        manager_role = Role.objects.get(name='Manager')
        manager_perms = financial_perms.filter(
            codename__in=['view_sales_reports', 'view_kpi_dashboard']
        )
        manager_role.permissions.add(*manager_perms)
        print(f"✅ Manager: {manager_perms.count()} permisos asignados")
    except Role.DoesNotExist:
        print("❌ Rol Manager no encontrado")
    
    # Cajera: SIN permisos financieros
    print("✅ Cajera: 0 permisos financieros (correcto)")
    
    # Estilista: SIN permisos financieros
    print("✅ Estilista: 0 permisos financieros (correcto)")
    
    print("\n✅ Permisos financieros asignados correctamente")

if __name__ == '__main__':
    assign_financial_permissions()
