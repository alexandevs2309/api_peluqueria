from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollPeriod

employee = Employee.objects.filter(user__email='alejaduarte@gmail.com').first()

if employee:
    # Obtener período abierto actual
    period = PayrollPeriod.objects.filter(
        employee=employee,
        status='open'
    ).first()
    
    if period:
        print(f"Período actual: {period.id} - {period.period_display}")
        print(f"Antes: Gross={period.gross_amount}, Commission={period.commission_earnings}")
        
        # Recalcular
        period.calculate_amounts()
        period.save()
        
        print(f"Después: Gross={period.gross_amount}, Commission={period.commission_earnings}")
    else:
        print("No hay período abierto")
else:
    print("Empleado no encontrado")
