#!/usr/bin/env python3
"""
AUDITORÍA FUNCIONAL - MÓDULO NÓMINA SIMPLE
Verificación de montos, estados y lógica sin aplicar cambios
"""
import os
import sys
import django
from decimal import Decimal
from django.utils import timezone

# Setup Django
sys.path.append('/home/alexander/Escritorio/clone/api_peluqueria-master')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee, Earning
from apps.payroll_api.models import PayrollSettlement, SettlementEarning
from apps.employees_api.payroll_models import PayrollPayment

def auditoria_nomina_simple():
    """Auditoría funcional completa del módulo de Nómina Simple"""
    print("🔍 AUDITORÍA FUNCIONAL - MÓDULO NÓMINA SIMPLE")
    print("=" * 80)
    print("OBJETIVO: Verificar correctitud de montos y estados SIN aplicar cambios")
    print()
    
    # Obtener empleados del estado observado
    empleados_auditoria = [
        'jhoangeraldo@gmail.com',
        'a.nicole.amejia@gmail.com', 
        'radhamerosario@gmail.com'
    ]
    
    # Buscar empleado con $0.00 (fixed)
    empleados_fixed = Employee.objects.filter(
        salary_type='fixed',
        is_active=True
    ).select_related('user')
    
    if empleados_fixed.exists():
        empleados_auditoria.append(empleados_fixed.first().user.email)
    
    print("📋 EMPLEADOS EN AUDITORÍA:")
    for email in empleados_auditoria:
        print(f"   - {email}")
    print()
    
    # Auditar cada empleado
    for email in empleados_auditoria:
        try:
            employee = Employee.objects.select_related('user').get(user__email=email)
            auditar_empleado(employee)
        except Employee.DoesNotExist:
            print(f"❌ Empleado {email} no encontrado")
            print()
    
    # Verificar lógica de sueldo fijo
    verificar_logica_sueldo_fijo()
    
    # Resumen final
    generar_resumen_auditoria()

def auditar_empleado(employee):
    """Auditar un empleado específico"""
    print(f"👤 EMPLEADO: {employee.user.full_name or employee.user.email}")
    print(f"   Email: {employee.user.email}")
    print(f"   ID: {employee.id}")
    print()
    
    # 1. Configuración del empleado
    print("⚙️  CONFIGURACIÓN:")
    print(f"   salary_type: {employee.salary_type}")
    print(f"   commission_payment_mode: {employee.commission_payment_mode}")
    print(f"   commission_percentage: {employee.commission_percentage}%")
    print(f"   contractual_monthly_salary: ${employee.contractual_monthly_salary}")
    print(f"   is_active: {employee.is_active}")
    print()
    
    # 2. Earnings del empleado
    print("💰 EARNINGS (employees_api.Earning):")
    earnings = Earning.objects.filter(employee=employee).order_by('-created_at')[:10]
    
    if earnings.exists():
        total_earnings = sum(e.amount for e in earnings)
        print(f"   Total earnings encontrados: {earnings.count()}")
        print(f"   Suma total: ${total_earnings}")
        print("   Últimos 5 earnings:")
        for earning in earnings[:5]:
            print(f"     - ${earning.amount} | {earning.created_at.date()} | Sale: {earning.sale_id}")
    else:
        print("   ❌ NO hay earnings registrados")
    print()
    
    # 3. PayrollSettlements del empleado
    print("📊 PAYROLL SETTLEMENTS:")
    settlements = PayrollSettlement.objects.filter(employee=employee).order_by('-created_at')[:5]
    
    if settlements.exists():
        for settlement in settlements:
            print(f"   Settlement ID: {settlement.id}")
            print(f"     Período: {settlement.period_start} - {settlement.period_end}")
            print(f"     Estado: {settlement.status}")
            print(f"     Bruto: ${settlement.gross_amount}")
            print(f"     Neto: ${settlement.net_amount}")
            print(f"     Comisión: ${settlement.commission_amount}")
            print(f"     Sueldo fijo: ${settlement.fixed_salary_amount}")
            
            # Verificar earnings asociados
            settlement_earnings = SettlementEarning.objects.filter(settlement=settlement)
            if settlement_earnings.exists():
                total_earnings_settlement = sum(se.earning_amount for se in settlement_earnings)
                print(f"     Earnings asociados: {settlement_earnings.count()} (${total_earnings_settlement})")
            else:
                print(f"     Earnings asociados: 0")
            print()
    else:
        print("   ❌ NO hay settlements registrados")
    print()
    
    # 4. Pagos realizados
    print("💳 PAGOS REALIZADOS (PayrollPayment):")
    payments = PayrollPayment.objects.filter(employee=employee).order_by('-paid_at')[:3]
    
    if payments.exists():
        for payment in payments:
            print(f"   Pago ID: {payment.payment_id}")
            print(f"     Fecha: {payment.paid_at.date()}")
            print(f"     Bruto: ${payment.gross_amount}")
            print(f"     Neto: ${payment.net_amount}")
            print(f"     Estado: {payment.status}")
    else:
        print("   ❌ NO hay pagos registrados")
    print()
    
    # 5. Análisis de correctitud
    analizar_correctitud_empleado(employee, earnings, settlements)
    
    print("-" * 80)
    print()

def analizar_correctitud_empleado(employee, earnings, settlements):
    """Analizar si los montos del empleado son correctos"""
    print("🔍 ANÁLISIS DE CORRECTITUD:")
    
    if not settlements.exists():
        print("   ⚠️  Sin settlements - No se puede verificar")
        return
    
    settlement_actual = settlements.first()
    
    # Verificar según tipo de salario
    if employee.salary_type == 'commission':
        if settlement_actual.commission_amount > 0 and settlement_actual.fixed_salary_amount == 0:
            print("   ✅ CORRECTO: Empleado commission solo tiene comisión")
        elif settlement_actual.gross_amount == 0:
            print("   ⚠️  POSIBLE: Empleado commission sin earnings = $0")
        else:
            print("   ❓ REVISAR: Empleado commission con configuración inesperada")
    
    elif employee.salary_type == 'fixed':
        if settlement_actual.gross_amount == 0:
            print("   ❓ REVISAR: Empleado fixed con $0 - ¿Falta lógica de sueldo fijo?")
        elif settlement_actual.fixed_salary_amount > 0:
            print("   ✅ CORRECTO: Empleado fixed con sueldo fijo calculado")
        else:
            print("   ❓ REVISAR: Empleado fixed sin sueldo fijo")
    
    elif employee.salary_type == 'mixed':
        if settlement_actual.commission_amount > 0 and settlement_actual.fixed_salary_amount == 0:
            print("   ⚠️  PARCIAL: Empleado mixed solo con comisión (¿falta parte fija?)")
        elif settlement_actual.commission_amount > 0 and settlement_actual.fixed_salary_amount > 0:
            print("   ✅ CORRECTO: Empleado mixed con ambos componentes")
        else:
            print("   ❓ REVISAR: Empleado mixed con configuración inesperada")
    
    # Verificar coherencia con earnings
    if earnings.exists():
        total_earnings = sum(e.amount for e in earnings)
        if settlement_actual.commission_amount > 0:
            porcentaje_esperado = employee.commission_percentage / 100
            comision_esperada = total_earnings * porcentaje_esperado
            if abs(settlement_actual.commission_amount - comision_esperada) < 1:
                print(f"   ✅ COHERENTE: Comisión calculada correctamente (${comision_esperada:.2f})")
            else:
                print(f"   ❓ REVISAR: Comisión esperada ${comision_esperada:.2f}, actual ${settlement_actual.commission_amount}")

def verificar_logica_sueldo_fijo():
    """Verificar si existe lógica de sueldo fijo en Nómina Simple"""
    print("🔧 VERIFICACIÓN LÓGICA SUELDO FIJO:")
    print()
    
    # Buscar empleados fixed con settlements
    empleados_fixed = Employee.objects.filter(
        salary_type='fixed',
        is_active=True
    )
    
    print(f"   Empleados con salary_type='fixed': {empleados_fixed.count()}")
    
    settlements_fixed = PayrollSettlement.objects.filter(
        employee__salary_type='fixed',
        fixed_salary_amount__gt=0
    )
    
    print(f"   Settlements con fixed_salary_amount > 0: {settlements_fixed.count()}")
    
    if settlements_fixed.exists():
        print("   ✅ EXISTE lógica de sueldo fijo")
        for settlement in settlements_fixed[:3]:
            print(f"     - Empleado: {settlement.employee.user.email}")
            print(f"       Sueldo fijo: ${settlement.fixed_salary_amount}")
            print(f"       Salario contractual: ${settlement.employee.contractual_monthly_salary}")
    else:
        print("   ❌ NO EXISTE lógica de sueldo fijo activa")
        print("   ⚠️  Empleados 'fixed' tendrán $0.00 (comportamiento esperado)")
    
    print()

def generar_resumen_auditoria():
    """Generar resumen final de la auditoría"""
    print("📋 RESUMEN DE AUDITORÍA:")
    print("=" * 80)
    
    # Contar por tipo de salario
    commission_count = Employee.objects.filter(salary_type='commission', is_active=True).count()
    fixed_count = Employee.objects.filter(salary_type='fixed', is_active=True).count()
    mixed_count = Employee.objects.filter(salary_type='mixed', is_active=True).count()
    
    print(f"📊 DISTRIBUCIÓN DE EMPLEADOS:")
    print(f"   Commission: {commission_count}")
    print(f"   Fixed: {fixed_count}")
    print(f"   Mixed: {mixed_count}")
    print()
    
    # Verificar settlements con montos
    settlements_con_monto = PayrollSettlement.objects.filter(gross_amount__gt=0).count()
    settlements_sin_monto = PayrollSettlement.objects.filter(gross_amount=0).count()
    
    print(f"📊 SETTLEMENTS:")
    print(f"   Con monto > $0: {settlements_con_monto}")
    print(f"   Con monto = $0: {settlements_sin_monto}")
    print()
    
    # Verificar earnings totales
    total_earnings = Earning.objects.count()
    empleados_con_earnings = Earning.objects.values('employee').distinct().count()
    
    print(f"📊 EARNINGS:")
    print(f"   Total earnings: {total_earnings}")
    print(f"   Empleados con earnings: {empleados_con_earnings}")
    print()
    
    print("✅ AUDITORÍA COMPLETADA")

if __name__ == "__main__":
    auditoria_nomina_simple()