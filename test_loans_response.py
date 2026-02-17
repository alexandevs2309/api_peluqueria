from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollDeduction
import json

employee = Employee.objects.filter(user__email='alejaduarte@gmail.com').first()

if employee:
    loan_deductions = PayrollDeduction.objects.filter(
        period__employee=employee,
        deduction_type__in=['loan', 'advance', 'emergency_loan']
    ).select_related('period').order_by('-created_at')
    
    type_labels = {
        'advance': 'Anticipo de Sueldo',
        'loan': 'Préstamo Personal',
        'emergency_loan': 'Préstamo de Emergencia'
    }
    
    loans_data = [{
        'id': d.id,
        'request_date': d.created_at.isoformat(),
        'type': d.deduction_type,
        'type_display': type_labels.get(d.deduction_type, d.deduction_type),
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
