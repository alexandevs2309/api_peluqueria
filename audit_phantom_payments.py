#!/usr/bin/env python
"""
AUDITORÍA DE PAGOS FANTASMA
Detecta FortnightSummary marcados como pagados sin evento de pago real
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import FortnightSummary
from django.utils import timezone

def audit_phantom_payments():
    """Detectar pagos fantasma en el sistema"""
    
    print("🔍 AUDITORÍA DE PAGOS FANTASMA")
    print("=" * 50)
    
    # Buscar summaries marcados como pagados
    paid_summaries = FortnightSummary.objects.filter(is_paid=True)
    
    phantom_payments = []
    
    for summary in paid_summaries:
        # Verificar si tiene datos de pago real
        has_payment_data = any([
            summary.paid_by,
            summary.payment_method,
            summary.payment_reference,
            summary.amount_paid and summary.amount_paid > 0
        ])
        
        # Verificar si tiene fecha de pago
        has_paid_date = summary.paid_at is not None
        
        # Es fantasma si está marcado como pagado pero sin datos de pago
        is_phantom = not has_payment_data
        
        if is_phantom:
            phantom_payments.append({
                'employee': summary.employee.user.full_name or summary.employee.user.email,
                'employee_id': summary.employee.id,
                'period': f"{summary.fortnight_year}/{summary.fortnight_number}",
                'amount': float(summary.total_earnings),
                'is_paid': summary.is_paid,
                'paid_at': summary.paid_at,
                'paid_by': summary.paid_by,
                'payment_method': summary.payment_method,
                'payment_reference': summary.payment_reference,
                'amount_paid': summary.amount_paid,
                'has_payment_data': has_payment_data,
                'has_paid_date': has_paid_date
            })
    
    print(f"📊 RESULTADOS:")
    print(f"   Total summaries pagados: {paid_summaries.count()}")
    print(f"   🚨 PAGOS FANTASMA detectados: {len(phantom_payments)}")
    print()
    
    if phantom_payments:
        print("🚨 PAGOS FANTASMA DETECTADOS:")
        print("-" * 80)
        for phantom in phantom_payments:
            print(f"👤 {phantom['employee']} (ID: {phantom['employee_id']})")
            print(f"   📅 Período: {phantom['period']}")
            print(f"   💰 Monto: ${phantom['amount']}")
            print(f"   ✅ is_paid: {phantom['is_paid']}")
            print(f"   📆 paid_at: {phantom['paid_at']}")
            print(f"   👨‍💼 paid_by: {phantom['paid_by']}")
            print(f"   💳 payment_method: {phantom['payment_method']}")
            print(f"   🔗 payment_reference: {phantom['payment_reference']}")
            print(f"   💵 amount_paid: {phantom['amount_paid']}")
            print()
    
    return phantom_payments

def fix_phantom_payments():
    """Corregir pagos fantasma marcándolos como no pagados"""
    
    phantom_payments = audit_phantom_payments()
    
    if not phantom_payments:
        print("✅ No se encontraron pagos fantasma para corregir")
        return
    
    print(f"🔧 CORRIGIENDO {len(phantom_payments)} PAGOS FANTASMA...")
    
    fixed_count = 0
    for phantom in phantom_payments:
        try:
            summary = FortnightSummary.objects.get(
                employee_id=phantom['employee_id'],
                fortnight_year=phantom['period'].split('/')[0],
                fortnight_number=phantom['period'].split('/')[1]
            )
            
            # Marcar como NO pagado
            summary.is_paid = False
            summary.paid_at = None
            summary.paid_by = None
            summary.payment_method = None
            summary.payment_reference = None
            summary.amount_paid = None
            summary.save()
            
            print(f"✅ Corregido: {phantom['employee']} - {phantom['period']}")
            fixed_count += 1
            
        except Exception as e:
            print(f"❌ Error corrigiendo {phantom['employee']}: {str(e)}")
    
    print(f"🎉 CORRECCIÓN COMPLETADA: {fixed_count} pagos fantasma corregidos")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--fix":
        fix_phantom_payments()
    else:
        audit_phantom_payments()
        print()
        print("💡 Para corregir los pagos fantasma, ejecute:")
        print("   python audit_phantom_payments.py --fix")