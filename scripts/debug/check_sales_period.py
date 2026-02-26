from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollPeriod
from apps.pos_api.models import Sale

employee = Employee.objects.filter(user__email='alejaduarte@gmail.com').first()

if employee:
    print(f"Empleado: {employee.user.full_name}")
    
    # Ver períodos
    periods = PayrollPeriod.objects.filter(employee=employee)
    print(f"\nPeríodos: {periods.count()}")
    for p in periods:
        print(f"  - {p.period_display} | Status: {p.status} | Gross: {p.gross_amount}")
    
    # Ver ventas
    sales = Sale.objects.filter(employee=employee).order_by('-date_time')[:5]
    print(f"\nVentas recientes: {sales.count()}")
    for s in sales:
        print(f"  - ID: {s.id} | Total: {s.total} | Fecha: {s.date_time} | Period: {s.period_id if hasattr(s, 'period') else 'N/A'}")
else:
    print("Empleado no encontrado")
