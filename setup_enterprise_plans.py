#!/usr/bin/env python3
"""
Script para configurar planes empresariales con soporte multi-sucursal
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.subscriptions_api.models import SubscriptionPlan

def setup_enterprise_plans():
    """Configurar planes con soporte multi-sucursal"""
    print("🏢 Configurando planes empresariales...")
    
    # Actualizar plan Enterprise para permitir múltiples sucursales
    enterprise_plan, created = SubscriptionPlan.objects.get_or_create(
        name='enterprise',
        defaults={
            'description': 'Plan Empresarial - Cadenas de barberías',
            'price': 199.99,
            'duration_month': 1,
            'is_active': True,
            'max_employees': 999,
            'max_users': 50,
            'allows_multiple_branches': True,
            'features': {
                'unlimited_appointments': True,
                'advanced_reports': True,
                'multi_branch_support': True,
                'custom_branding': True,
                'priority_support': True,
                'api_access': True
            }
        }
    )
    
    if not created:
        enterprise_plan.allows_multiple_branches = True
        enterprise_plan.save()
        print("✅ Plan Enterprise actualizado con soporte multi-sucursal")
    else:
        print("✅ Plan Enterprise creado con soporte multi-sucursal")
    
    # Asegurar que otros planes NO permitan múltiples sucursales
    other_plans = SubscriptionPlan.objects.exclude(name='enterprise')
    for plan in other_plans:
        if plan.allows_multiple_branches:
            plan.allows_multiple_branches = False
            plan.save()
            print(f"✅ Plan {plan.get_name_display()} configurado como single-branch")
    
    print("🎉 Configuración completada!")
    print("\n📋 Resumen:")
    for plan in SubscriptionPlan.objects.all():
        branches = "Multi-sucursal" if plan.allows_multiple_branches else "Una sucursal"
        print(f"  • {plan.get_name_display()}: {branches}")

if __name__ == "__main__":
    setup_enterprise_plans()