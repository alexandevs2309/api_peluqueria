#!/usr/bin/env python
"""
AUDITORÍA DETALLADA DE PAGOS
Analiza todos los pagos y su origen
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import FortnightSummary
from django.utils import timezone

def detailed_payment_audit():
    """Análisis detallado de todos los pagos"""
    
    print("🔍 AUDITORÍA DETALLADA DE PAGOS")
    print("=" * 60)
    
    # Obtener todos los summaries
    all_summaries = FortnightSummary.objects.all().order_by('-fortnight_year', '-fortnight_number')
    
    print(f"📊 Total FortnightSummary encontrados: {all_summaries.count()}")
    print()
    
    paid_summaries = []
    unpaid_summaries = []
    
    for summary in all_summaries:
        employee_name = summary.employee.user.full_name or summary.employee.user.email
        
        summary_data = {
            'employee': employee_name,
            'employee_id': summary.employee.id,
            'salary_type': summary.employee.salary_type,
            'period': f"{summary.fortnight_year}/{summary.fortnight_number}",
            'total_earnings': float(summary.total_earnings),
            'is_paid': summary.is_paid,
            'paid_at': summary.paid_at,
            'paid_by': summary.paid_by.email if summary.paid_by else None,
            'payment_method': summary.payment_method,
            'payment_reference': summary.payment_reference,
            'amount_paid': float(summary.amount_paid) if summary.amount_paid else None,
            'net_salary': float(summary.net_salary) if summary.net_salary else None,
            'is_advance_payment': getattr(summary, 'is_advance_payment', False),
            'created_at': summary.created_at,
            'updated_at': summary.updated_at
        }
        
        if summary.is_paid:
            paid_summaries.append(summary_data)
        else:
            unpaid_summaries.append(summary_data)
    
    print("💰 PAGOS REALIZADOS:")
    print("-" * 60)
    if paid_summaries:
        for payment in paid_summaries:
            print(f"👤 {payment['employee']} (ID: {payment['employee_id']})")
            print(f"   📅 Período: {payment['period']}")
            print(f"   💰 Ganancia: ${payment['total_earnings']}")
            print(f"   💵 Pagado: ${payment['amount_paid'] or 'N/A'}")
            print(f"   💳 Método: {payment['payment_method'] or 'N/A'}")
            print(f"   📆 Fecha pago: {payment['paid_at']}")
            print(f"   👨💼 Pagado por: {payment['paid_by'] or 'N/A'}")
            print(f"   🔗 Referencia: {payment['payment_reference'] or 'N/A'}")
            print(f"   ⚡ Adelanto: {payment['is_advance_payment']}")
            print(f"   📝 Tipo salario: {payment['salary_type']}")
            print(f"   🕐 Creado: {payment['created_at']}")
            print(f"   🕐 Actualizado: {payment['updated_at']}")
            print()
    else:
        print("   ✅ No hay pagos realizados")
    
    print("⏳ PAGOS PENDIENTES:")
    print("-" * 60)
    if unpaid_summaries:
        for pending in unpaid_summaries:
            print(f"👤 {pending['employee']} (ID: {pending['employee_id']})")
            print(f"   📅 Período: {pending['period']}")
            print(f"   💰 Ganancia: ${pending['total_earnings']}")
            print(f"   📝 Tipo salario: {pending['salary_type']}")
            print(f"   🕐 Creado: {pending['created_at']}")
            print()
    else:
        print("   ✅ No hay pagos pendientes")
    
    # Análisis de empleados
    print("👥 ANÁLISIS POR EMPLEADO:")
    print("-" * 60)
    employees = Employee.objects.filter(is_active=True)
    for employee in employees:
        employee_summaries = all_summaries.filter(employee=employee)
        paid_count = employee_summaries.filter(is_paid=True).count()
        pending_count = employee_summaries.filter(is_paid=False).count()
        
        print(f"👤 {employee.user.full_name or employee.user.email} (ID: {employee.id})")
        print(f"   📝 Tipo salario: {employee.salary_type}")
        print(f"   💰 Salario contractual: ${employee.contractual_monthly_salary}")
        print(f"   📊 Períodos pagados: {paid_count}")
        print(f"   ⏳ Períodos pendientes: {pending_count}")
        print(f"   📈 Total períodos: {employee_summaries.count()}")
        print()
    
    return {
        'total_summaries': all_summaries.count(),
        'paid_summaries': len(paid_summaries),
        'unpaid_summaries': len(unpaid_summaries),
        'paid_details': paid_summaries,
        'unpaid_details': unpaid_summaries
    }

if __name__ == "__main__":
    detailed_payment_audit()