#!/usr/bin/env python
"""
Test de correcciones estructurales del módulo de pagos
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.employees_api.models import Employee
from apps.employees_api.period_utils import get_current_period_for_employee, get_period_dates
from apps.pos_api.models import Sale
from django.utils import timezone
import requests

def test_period_calculations():
    """Probar cálculos de períodos por frecuencia"""
    print("🔍 PROBANDO CÁLCULOS DE PERÍODOS")
    print("=" * 50)
    
    employees = Employee.objects.filter(is_active=True)
    
    for employee in employees:
        print(f"👤 {employee.user.full_name or employee.user.email}")
        print(f"   📝 Tipo salario: {employee.salary_type}")
        print(f"   📅 Frecuencia: {getattr(employee, 'payment_frequency', 'biweekly')}")
        
        # Obtener período actual
        current_period = get_current_period_for_employee(employee)
        print(f"   📊 Período actual: {current_period}")
        
        # Obtener fechas específicas
        period_start, period_end = get_period_dates(employee, 2025, 23)
        print(f"   📆 Fechas período 2025/23: {period_start} - {period_end}")
        
        # Contar ventas en el período
        if employee.salary_type == 'commission':
            period_sales = Sale.objects.filter(
                employee=employee,
                status='completed',
                period__isnull=True,
                date_time__date__gte=current_period['start_date'],
                date_time__date__lte=current_period['end_date']
            )
            print(f"   💰 Ventas en período actual: {period_sales.count()}")
        
        print()

def test_earnings_summary_api():
    """Probar API de resumen de ganancias corregida"""
    print("🔍 PROBANDO API EARNINGS_SUMMARY CORREGIDA")
    print("=" * 50)
    
    # Simular request a la API
    url = "http://localhost:8000/api/employees/payments/earnings_summary/"
    
    try:
        response = requests.get(url, headers={
            'Authorization': 'Bearer YOUR_TOKEN_HERE'  # Reemplazar con token real
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API respondió correctamente")
            print(f"📊 Total empleados: {len(data.get('employees', []))}")
            
            for emp in data.get('employees', [])[:3]:  # Mostrar primeros 3
                print(f"👤 {emp['employee_name']}")
                print(f"   📝 Tipo: {emp['salary_type']}")
                print(f"   📅 Frecuencia: {emp.get('payment_frequency', 'N/A')}")
                print(f"   💰 Pendiente: ${emp['pending_amount']}")
                print(f"   🔗 Sale IDs: {len(emp['pending_sale_ids'])} ventas")
                print(f"   📆 Período: {emp['period_dates']}")
                print()
        else:
            print(f"❌ Error API: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error conectando API: {str(e)}")

def test_commission_filtering():
    """Probar filtrado de comisiones por período"""
    print("🔍 PROBANDO FILTRADO DE COMISIONES POR PERÍODO")
    print("=" * 50)
    
    commission_employees = Employee.objects.filter(
        salary_type='commission',
        is_active=True
    )
    
    for employee in commission_employees:
        print(f"👤 {employee.user.full_name or employee.user.email}")
        
        # Período actual
        current_period = get_current_period_for_employee(employee)
        
        # Ventas del período actual
        period_sales = Sale.objects.filter(
            employee=employee,
            status='completed',
            period__isnull=True,
            date_time__date__gte=current_period['start_date'],
            date_time__date__lte=current_period['end_date']
        )
        
        # Todas las ventas pendientes (método anterior)
        all_pending_sales = Sale.objects.filter(
            employee=employee,
            status='completed',
            period__isnull=True
        )
        
        print(f"   📅 Período: {current_period['start_date']} - {current_period['end_date']}")
        print(f"   ✅ Ventas del período: {period_sales.count()}")
        print(f"   📊 Total ventas pendientes: {all_pending_sales.count()}")
        
        if period_sales.count() != all_pending_sales.count():
            print(f"   🎯 CORRECCIÓN APLICADA: Filtrado por período funciona")
        else:
            print(f"   ℹ️  Mismo resultado (normal si todas las ventas son del período)")
        
        print()

if __name__ == "__main__":
    test_period_calculations()
    test_commission_filtering()
    print("💡 Para probar la API, configure un token de autenticación válido")
    print("   y ejecute test_earnings_summary_api()")