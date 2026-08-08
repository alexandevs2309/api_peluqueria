from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollDeduction

employee = Employee.objects.filter(user__email='alejaduarte@gmail.com').first()

if employee:
    loans = PayrollDeduction.objects.filter(
        period__employee=employee,
        deduction_type__in=['loan', 'advance']
    )
    
    print(f"Total préstamos: {loans.count()}")
    for loan in loans:
        print(f"\nID: {loan.id}")
        print(f"Type: '{loan.deduction_type}'")
        print(f"Amount: {loan.amount}")
        print(f"Description: {loan.description}")
        print(f"Installments: {loan.installments}")
else:
    print("Empleado no encontrado")
