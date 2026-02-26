from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollPeriod
from apps.pos_api.models import Sale

employee = Employee.objects.filter(user__email='alejaduarte@gmail.com').first()

if employee:
    period = PayrollPeriod.objects.filter(employee=employee, status='open').first()
    
    if period:
        print(f"Período: {period.id} - {period.period_display}")
        print(f"Rango: {period.period_start} a {period.period_end}")
        
        # Buscar ventas en el rango
        sales = Sale.objects.filter(
            employee=employee,
            date_time__date__gte=period.period_start,
            date_time__date__lte=period.period_end
        )
        
        print(f"\nVentas en el período: {sales.count()}")
        for s in sales:
            print(f"  - ID: {s.id} | Total: {s.total} | Fecha: {s.date_time.date()}")
            print(f"    commission_rate_snapshot: {s.commission_rate_snapshot}")
            print(f"    commission_amount_snapshot: {s.commission_amount_snapshot}")
