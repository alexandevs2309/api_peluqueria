from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollDeduction
import json

def _main():
    employee = Employee.objects.filter(user__email='alejaduarte@gmail.com').first()

    if employee:
        loan_deductions = PayrollDeduction.objects.filter(
            period__employee=employee,
            deduction_type__in=['loan', 'advance']
        ).select_related('period').order_by('-created_at')
        
        loans_data = [{
            'id': d.id,
            'request_date': d.created_at.isoformat(),
            'type': 'Préstamo' if d.deduction_type == 'loan' else 'Adelanto',
            'installments': d.installments,
            'monthly_payment': float(d.amount),
            'remaining_balance': float(d.amount) if d.period.status != 'paid' else 0,
            'status': 'Pagado' if d.period.status == 'paid' else 'Pendiente',
            'reason': d.description or 'Sin motivo',
            'amount': float(d.amount),
            'period': d.period.period_display,
            'period_status': d.period.status
        } for d in loan_deductions]
        
        print(json.dumps(loans_data, indent=2, ensure_ascii=False))
    else:
        print("Empleado no encontrado")


if __name__ == '__main__':
    _main()
