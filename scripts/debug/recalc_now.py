from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollPeriod

employee = Employee.objects.filter(user__email='alejaduarte@gmail.com').first()

if employee:
    period = PayrollPeriod.objects.filter(employee=employee, status='open').first()
    
    if period:
        print(f"Antes: Gross=${period.gross_amount}, Commission=${period.commission_earnings}")
        
        period.calculate_amounts()
        period.save()
        
        print(f"Después: Gross=${period.gross_amount}, Commission=${period.commission_earnings}")
