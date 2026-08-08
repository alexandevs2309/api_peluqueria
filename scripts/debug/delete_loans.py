from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollDeduction

# Buscar empleado
employee = Employee.objects.filter(user__email='alejaduarte@gmail.com').first()

if employee:
    # Eliminar todos los préstamos
    deleted = PayrollDeduction.objects.filter(
        period__employee=employee,
        deduction_type__in=['loan', 'advance']
    ).delete()
    
    print(f"Empleado: {employee.user.full_name}")
    print(f"Préstamos eliminados: {deleted[0]}")
else:
    print("Empleado no encontrado")
