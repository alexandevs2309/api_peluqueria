from apps.pos_api.models import Sale
from apps.employees_api.models import Employee

employee = Employee.objects.filter(user__email='alejaduarte@gmail.com').first()

if employee:
    # Última venta
    sale = Sale.objects.filter(employee=employee).order_by('-date_time').first()
    
    if sale:
        print(f"Última venta: ID {sale.id}")
        print(f"Total: ${sale.total}")
        print(f"Fecha: {sale.date_time}")
        print(f"Employee: {sale.employee}")
        print(f"Period: {sale.period_id}")
        print(f"Commission rate snapshot: {sale.commission_rate_snapshot}")
        print(f"Commission amount snapshot: {sale.commission_amount_snapshot}")
        
        if sale.period:
            print(f"\nPeríodo: {sale.period.period_display}")
            print(f"Gross: ${sale.period.gross_amount}")
            print(f"Commission: ${sale.period.commission_earnings}")
