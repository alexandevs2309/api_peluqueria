"""
Servicios de nómina - Capa de lógica de negocio
"""
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db import transaction
from .models import Employee
# ARCHIVO LEGACY - FortnightSummary eliminado
# Usar payroll_api.PayrollSettlement en su lugar
from .payroll_calculator import calculate_net_salary, get_payroll_summary

class PayrollService:
    @staticmethod
    def generate_paystub_for_period(employee, gross_amount, year, fortnight):
        """Genera recibo de pago para un empleado en un período"""
        with transaction.atomic():
            summary, created = FortnightSummary.objects.get_or_create(
                employee=employee,
                fortnight_year=year,
                fortnight_number=fortnight,
                defaults={'total_earnings': Decimal('0.00')}
            )
            
            if summary.is_paid:
                raise ValueError(f"Período ya pagado para {employee.user.full_name}")
            
            # Calcular descuentos
            net_salary, deductions = calculate_net_salary(gross_amount, is_fortnight=True)
            
            # Actualizar summary
            summary.total_earnings = gross_amount
            summary.afp_deduction = deductions['afp']
            summary.sfs_deduction = deductions['sfs']
            summary.isr_deduction = deductions['isr']
            summary.total_deductions = deductions['total']
            summary.net_salary = net_salary
            summary.save()
            
            return summary
    
    @staticmethod
    def bulk_generate_for_period(tenant, year, fortnight, employee_ids=None):
        """Genera recibos masivos para un período"""
        employees = Employee.objects.filter(tenant=tenant, is_active=True)
        if employee_ids:
            employees = employees.filter(id__in=employee_ids)
        
        results = {'success': [], 'errors': []}
        
        for emp in employees:
            try:
                # Calcular salario bruto según tipo
                if emp.salary_type == 'fixed':
                    gross = emp.salary_amount
                else:
                    # Para comisión, obtener de ventas
                    from apps.pos_api.models import Sale
                    from datetime import datetime, timedelta
                    
                    month = ((fortnight - 1) // 2) + 1
                    is_first = (fortnight % 2) == 1
                    start_day = 1 if is_first else 16
                    end_day = 15 if is_first else 28
                    
                    start_date = datetime(year, month, start_day).date()
                    end_date = datetime(year, month, end_day).date()
                    
                    sales = Sale.objects.filter(
                        employee=emp,
                        date_time__date__gte=start_date,
                        date_time__date__lte=end_date
                    )
                    total_sales = sum(float(s.total) for s in sales)
                    gross = Decimal(str(total_sales * float(emp.commission_percentage or 60) / 100))
                
                if gross > 0:
                    summary = PayrollService.generate_paystub_for_period(emp, gross, year, fortnight)
                    results['success'].append({
                        'employee_id': emp.id,
                        'employee_name': emp.user.full_name,
                        'gross': float(gross),
                        'net': float(summary.net_salary)
                    })
            except Exception as e:
                results['errors'].append({
                    'employee_id': emp.id,
                    'error': str(e)
                })
        
        return results
    
    @staticmethod
    def mark_paystub_as_paid(summary, paid_at, method, transaction_id):
        """Marca un recibo como pagado"""
        with transaction.atomic():
            summary.is_paid = True
            summary.paid_at = paid_at or timezone.now()
            summary.payment_method = method
            summary.payment_reference = transaction_id
            summary.amount_paid = summary.net_salary
            summary.save()
            
            # Crear recibo si no existe
            receipt, created = PaymentReceipt.objects.get_or_create(
                fortnight_summary=summary
            )
            
            return receipt
