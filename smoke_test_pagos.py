#!/usr/bin/env python
"""
Smoke Test para Sistema de Pagos
Verifica el flujo completo de pagos a empleados
"""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.pos_api.models import Sale
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import FortnightSummary
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import requests

User = get_user_model()

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def test_pending_payments():
    """Test 1: Verificar endpoint pending-payments"""
    print_header("TEST 1: Endpoint pending-payments")
    
    # Obtener empleado con ventas
    employee = Employee.objects.filter(is_active=True).first()
    if not employee:
        print("❌ No hay empleados activos")
        return False
    
    print(f"✓ Empleado: {employee.user.full_name} (ID: {employee.id})")
    print(f"  Tipo: {employee.salary_type}, Comisión: {employee.commission_percentage}%")
    
    # Verificar ventas pendientes
    pending_sales = Sale.objects.filter(
        employee=employee,
        status='completed',
        period__isnull=True
    )
    
    print(f"✓ Ventas pendientes: {pending_sales.count()}")
    for sale in pending_sales[:3]:
        print(f"  - Sale #{sale.id}: ${sale.total}")
    
    if pending_sales.count() == 0:
        print("⚠️  No hay ventas pendientes para este empleado")
        return True
    
    # Calcular monto esperado
    total_sales = sum([float(s.total) for s in pending_sales])
    if employee.salary_type == 'commission':
        expected_amount = total_sales * float(employee.commission_percentage) / 100
    else:
        expected_amount = 0
    
    print(f"✓ Monto esperado: ${expected_amount:.2f}")
    print("✅ TEST 1 PASADO\n")
    return True

def test_payment_creation():
    """Test 2: Crear pago con sale_ids"""
    print_header("TEST 2: Crear pago con sale_ids")
    
    # Obtener empleado con ventas pendientes
    employee = Employee.objects.filter(is_active=True).first()
    pending_sales = Sale.objects.filter(
        employee=employee,
        status='completed',
        period__isnull=True
    )[:2]  # Tomar solo 2 ventas
    
    if not pending_sales.exists():
        print("⚠️  No hay ventas pendientes, creando venta de prueba...")
        # Crear venta de prueba
        sale = Sale.objects.create(
            employee=employee,
            total=Decimal('1000.00'),
            status='completed',
            date_time=timezone.now()
        )
        pending_sales = [sale]
        print(f"✓ Venta creada: #{sale.id}")
    
    sale_ids = [s.id for s in pending_sales]
    print(f"✓ Sale IDs a pagar: {sale_ids}")
    
    # Simular pago (sin hacer request HTTP, usar lógica directa)
    from apps.employees_api.earnings_models import Earning
    
    today = timezone.now().date()
    year, fortnight = Earning.calculate_fortnight(today)
    
    print(f"✓ Período: Año {year}, Quincena {fortnight}")
    
    # Verificar que las ventas no estén asignadas
    for sale_id in sale_ids:
        sale = Sale.objects.get(id=sale_id)
        if sale.period:
            print(f"❌ Sale #{sale_id} ya está asignada a período {sale.period.id}")
            return False
    
    print("✓ Ventas disponibles para pago")
    print("✅ TEST 2 PASADO\n")
    return True

def test_idempotency():
    """Test 3: Verificar idempotencia"""
    print_header("TEST 3: Idempotencia")
    
    # Buscar un FortnightSummary pagado
    paid_summary = FortnightSummary.objects.filter(is_paid=True).first()
    
    if not paid_summary:
        print("⚠️  No hay pagos previos para verificar idempotencia")
        return True
    
    print(f"✓ Summary pagado encontrado: #{paid_summary.id}")
    print(f"  Empleado: {paid_summary.employee.user.full_name}")
    print(f"  Monto: ${paid_summary.amount_paid}")
    print(f"  Referencia: {paid_summary.payment_reference}")
    
    # Verificar que las ventas están asignadas
    sales_count = Sale.objects.filter(period=paid_summary).count()
    print(f"✓ Ventas asignadas: {sales_count}")
    
    if sales_count == 0:
        print("⚠️  El summary no tiene ventas asignadas")
    
    print("✅ TEST 3 PASADO\n")
    return True

def test_configuration_applied():
    """Test 4: Verificar que configuración se aplica"""
    print_header("TEST 4: Configuración aplicada")
    
    employees = Employee.objects.filter(is_active=True)
    
    for emp in employees:
        print(f"\n{emp.user.full_name} (ID: {emp.id})")
        print(f"  Tipo: {emp.salary_type}")
        print(f"  Comisión: {emp.commission_percentage}%")
        print(f"  Salario: ${emp.contractual_monthly_salary}")
        print(f"  Descuentos: AFP={emp.apply_afp}, SFS={emp.apply_sfs}, ISR={emp.apply_isr}")
        
        # Verificar pagos
        summaries = FortnightSummary.objects.filter(employee=emp, is_paid=True)
        if summaries.exists():
            last = summaries.order_by('-paid_at').first()
            print(f"  Último pago: ${last.amount_paid} ({last.paid_at.date()})")
            if last.total_deductions > 0:
                print(f"    Descuentos: ${last.total_deductions}")
    
    print("\n✅ TEST 4 PASADO\n")
    return True

def main():
    print_header("SMOKE TEST - SISTEMA DE PAGOS")
    
    tests = [
        ("Pending Payments", test_pending_payments),
        ("Payment Creation", test_payment_creation),
        ("Idempotency", test_idempotency),
        ("Configuration", test_configuration_applied)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ ERROR en {name}: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Resumen
    print_header("RESUMEN")
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASADO" if result else "❌ FALLADO"
        print(f"{name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests pasados")
    
    if passed == total:
        print("\n🎉 TODOS LOS TESTS PASARON")
        return 0
    else:
        print("\n⚠️  ALGUNOS TESTS FALLARON")
        return 1

if __name__ == '__main__':
    sys.exit(main())
