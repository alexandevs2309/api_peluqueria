#!/usr/bin/env python3
"""
Script para limpiar completamente el sistema de pagos y empezar de cero
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.append('/app')
django.setup()

from apps.employees_api.earnings_models import FortnightSummary, PaymentReceipt, Earning
from apps.employees_api.advance_loans import AdvanceLoan, LoanPayment
from apps.pos_api.models import Sale
from django.db import transaction

def reset_payroll_system():
    """Limpiar completamente el sistema de pagos"""
    
    print("🧹 LIMPIANDO SISTEMA DE PAGOS...")
    
    with transaction.atomic():
        # 1. Limpiar pagos y recibos
        print("Eliminando FortnightSummary y PaymentReceipt...")
        PaymentReceipt.objects.all().delete()
        FortnightSummary.objects.all().delete()
        
        # 2. Limpiar earnings antiguos
        print("Eliminando Earning...")
        Earning.objects.all().delete()
        
        # 3. Limpiar préstamos
        print("Eliminando préstamos y pagos...")
        LoanPayment.objects.all().delete()
        AdvanceLoan.objects.all().delete()
        
        # 4. Desasignar ventas de períodos
        print("Desasignando ventas de períodos...")
        Sale.objects.filter(period__isnull=False).update(period=None)
        
        print("✅ Sistema de pagos limpiado completamente")
        
        # Mostrar estado final
        print("\n=== ESTADO DESPUÉS DE LIMPIEZA ===")
        print(f"FortnightSummary: {FortnightSummary.objects.count()}")
        print(f"PaymentReceipt: {PaymentReceipt.objects.count()}")
        print(f"Earning: {Earning.objects.count()}")
        print(f"AdvanceLoan: {AdvanceLoan.objects.count()}")
        print(f"LoanPayment: {LoanPayment.objects.count()}")
        print(f"Sales con period: {Sale.objects.filter(period__isnull=False).count()}")
        print(f"Sales sin period: {Sale.objects.filter(period__isnull=True).count()}")
        
        print("\n🎉 SISTEMA LISTO PARA EMPEZAR DE CERO")

if __name__ == "__main__":
    confirm = input("¿Estás seguro de limpiar TODOS los datos de pagos? (escribe 'SI' para confirmar): ")
    
    if confirm == 'SI':
        reset_payroll_system()
    else:
        print("❌ Operación cancelada")