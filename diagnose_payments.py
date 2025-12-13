#!/usr/bin/env python3
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.employees_api.models import Employee
from apps.pos_api.models import Sale
from apps.employees_api.earnings_models import FortnightSummary
from django.db.models import Count, Sum, Q

User = get_user_model()

def diagnose():
    print('🔍 ANÁLISIS DETALLADO DE PAGOS')
    print('=' * 60)
    
    user = User.objects.get(email='alexanderdelrosarioperez@gmail.com')
    employees = Employee.objects.filter(tenant=user.tenant, is_active=True)
    
    for emp in employees:
        print(f'\n👤 EMPLEADO: {emp.user.full_name}')
        print(f'   Tipo: {emp.salary_type}')
        print(f'   Comisión: {emp.commission_percentage}%')
        
        # Ventas del empleado
        all_sales = Sale.objects.filter(employee=emp)
        pending_sales = all_sales.filter(period__isnull=True, status='completed')
        
        print(f'   📊 VENTAS:')
        print(f'      Total: {all_sales.count()}')
        print(f'      Pendientes: {pending_sales.count()}')
        
        if pending_sales.exists():
            total_pending = pending_sales.aggregate(total=Sum('total'))['total']
            print(f'      Monto pendiente: ${total_pending}')
        
        # Summaries del empleado
        summaries = FortnightSummary.objects.filter(employee=emp).order_by('-fortnight_year', '-fortnight_number')
        print(f'   💰 SUMMARIES: {summaries.count()}')
        
        for summary in summaries[:2]:
            status = '✅ PAGADO' if summary.is_paid else '⏳ PENDIENTE'
            print(f'      {summary.fortnight_display}: ${summary.total_earnings} - {status}')
    
    # Resumen general
    total_pending_sales = Sale.objects.filter(
        employee__tenant=user.tenant,
        period__isnull=True,
        status='completed'
    ).count()
    
    print(f'\n📈 RESUMEN:')
    print(f'   Empleados activos: {employees.count()}')
    print(f'   Ventas pendientes: {total_pending_sales}')

if __name__ == '__main__':
    diagnose()