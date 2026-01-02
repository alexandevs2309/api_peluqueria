"""
Sistema de nómina automática para sueldos fijos
"""
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from .models import Employee
# ARCHIVO LEGACY - FortnightSummary eliminado
# Usar payroll_api.PayrollSettlement en su lugar
from .tax_calculator_factory import TaxCalculatorFactory
import logging

logger = logging.getLogger(__name__)

class AutomaticPayrollProcessor:
    """Procesador de nómina automática"""
    
    def __init__(self, country_code='DO'):
        self.tax_calculator = TaxCalculatorFactory.get_calculator(country_code)
    
    def process_fixed_salaries(self, year=None, fortnight=None, tenant=None):
        """
        Procesar pagos automáticos para empleados con sueldo fijo
        
        Args:
            year: Año del pago (opcional, usa actual)
            fortnight: Quincena del pago (opcional, usa actual)
            tenant: Tenant específico (opcional, procesa todos)
        
        Returns:
            Dict con resultados del procesamiento
        """
        if not year or not fortnight:
            today = timezone.now().date()
            year, fortnight = self._calculate_fortnight(today)
        
        # Filtrar empleados con sueldo fijo
        employees_query = Employee.objects.filter(
            salary_type__in=['fixed', 'mixed'],
            is_active=True,
            contractual_monthly_salary__gt=0
        )
        
        if tenant:
            employees_query = employees_query.filter(tenant=tenant)
        
        employees = employees_query.select_related('user', 'tenant')
        
        results = {
            'processed': [],
            'skipped': [],
            'errors': [],
            'total_amount': Decimal('0'),
            'total_processed': 0
        }
        
        for employee in employees:
            try:
                result = self._process_employee_fixed_salary(employee, year, fortnight)
                if result['status'] == 'processed':
                    results['processed'].append(result)
                    results['total_amount'] += result['net_amount']
                    results['total_processed'] += 1
                else:
                    results['skipped'].append(result)
                    
            except Exception as e:
                logger.error(f"Error procesando empleado {employee.id}: {str(e)}")
                results['errors'].append({
                    'employee_id': employee.id,
                    'employee_name': employee.user.full_name or employee.user.email,
                    'error': str(e)
                })
        
        return results
    
    def _process_employee_fixed_salary(self, employee, year, fortnight):
        """
        Procesar pago de sueldo fijo para un empleado específico
        
        Args:
            employee: Instancia del empleado
            year: Año del pago
            fortnight: Quincena del pago
            
        Returns:
            Dict con resultado del procesamiento
        """
        with transaction.atomic():
            # Verificar si ya tiene pago para esta quincena
            existing_summary = FortnightSummary.objects.filter(
                employee=employee,
                fortnight_year=year,
                fortnight_number=fortnight,
                is_paid=True
            ).first()
            
            if existing_summary:
                return {
                    'status': 'skipped',
                    'reason': 'already_paid',
                    'employee_id': employee.id,
                    'employee_name': employee.user.full_name or employee.user.email,
                    'paid_at': existing_summary.paid_at.isoformat()
                }
            
            # Calcular monto del sueldo fijo
            gross_amount = self._calculate_fixed_salary_amount(employee)
            
            if gross_amount <= 0:
                return {
                    'status': 'skipped',
                    'reason': 'zero_amount',
                    'employee_id': employee.id,
                    'employee_name': employee.user.full_name or employee.user.email
                }
            
            # Calcular descuentos
            is_month_end = self.tax_calculator.is_month_end_payment(year, fortnight)
            deductions = self.tax_calculator.calculate_deductions(gross_amount, employee, is_month_end)
            net_amount = self.tax_calculator.get_net_amount(gross_amount, deductions)
            
            # Crear o actualizar FortnightSummary
            summary, created = FortnightSummary.objects.get_or_create(
                employee=employee,
                fortnight_year=year,
                fortnight_number=fortnight,
                defaults={
                    'total_earnings': gross_amount,
                    'total_services': 0,
                    'is_paid': True,
                    'paid_at': timezone.now(),
                    'payment_method': 'automatic',
                    'payment_reference': f'AUTO-{year}-{fortnight}-{employee.id}',
                    'net_salary': net_amount,
                    'amount_paid': net_amount,
                    'afp_deduction': deductions['afp'],
                    'sfs_deduction': deductions['sfs'],
                    'isr_deduction': deductions['isr'],
                    'total_deductions': deductions['total'],
                    'payment_notes': 'Pago automático de sueldo fijo'
                }
            )
            
            if not created and not summary.is_paid:
                # Actualizar summary existente no pagado
                summary.total_earnings = gross_amount
                summary.is_paid = True
                summary.paid_at = timezone.now()
                summary.payment_method = 'automatic'
                summary.payment_reference = f'AUTO-{year}-{fortnight}-{employee.id}'
                summary.net_salary = net_amount
                summary.amount_paid = net_amount
                summary.afp_deduction = deductions['afp']
                summary.sfs_deduction = deductions['sfs']
                summary.isr_deduction = deductions['isr']
                summary.total_deductions = deductions['total']
                summary.payment_notes = 'Pago automático de sueldo fijo'
                summary.save()
            
            # Crear recibo
            receipt, _ = PaymentReceipt.objects.get_or_create(
                fortnight_summary=summary,
                defaults={}
            )
            
            return {
                'status': 'processed',
                'employee_id': employee.id,
                'employee_name': employee.user.full_name or employee.user.email,
                'salary_type': employee.salary_type,
                'gross_amount': gross_amount,
                'net_amount': net_amount,
                'deductions': deductions,
                'receipt_number': receipt.receipt_number,
                'paid_at': summary.paid_at.isoformat()
            }
    
    def _calculate_fixed_salary_amount(self, employee):
        """
        Calcular monto de sueldo fijo según frecuencia de pago
        
        Args:
            employee: Instancia del empleado
            
        Returns:
            Decimal con monto a pagar
        """
        monthly_salary = employee.contractual_monthly_salary or Decimal('0')
        
        if monthly_salary <= 0:
            return Decimal('0')
        
        # Calcular según frecuencia de pago
        frequency = getattr(employee, 'payment_frequency', 'biweekly')
        
        if frequency == 'monthly':
            return monthly_salary
        elif frequency == 'biweekly':
            return monthly_salary / 2
        elif frequency == 'weekly':
            return monthly_salary / Decimal('4.333')  # ~4.33 semanas por mes
        elif frequency == 'daily':
            return monthly_salary / Decimal('23.83')  # ~23.83 días laborables por mes
        else:
            # Default: quincenal
            return monthly_salary / 2
    
    def _calculate_fortnight(self, date):
        """Calcular año y quincena para una fecha"""
        from .earnings_models import Earning
        return Earning.calculate_fortnight(date)
    
    def schedule_automatic_payments(self, tenant=None):
        """
        Programar pagos automáticos para la quincena actual
        
        Args:
            tenant: Tenant específico (opcional)
            
        Returns:
            Dict con resultados
        """
        today = timezone.now().date()
        year, fortnight = self._calculate_fortnight(today)
        
        # Solo procesar en días 15 y último del mes
        if today.day not in [15] and today != self._get_last_day_of_month(today):
            return {
                'status': 'skipped',
                'reason': 'not_payment_day',
                'date': today.isoformat()
            }
        
        return self.process_fixed_salaries(year, fortnight, tenant)
    
    def _get_last_day_of_month(self, date):
        """Obtener último día del mes"""
        from calendar import monthrange
        last_day = monthrange(date.year, date.month)[1]
        return date.replace(day=last_day)


# Función de conveniencia para usar en views
def process_automatic_payroll(tenant=None):
    """
    Función de conveniencia para procesar nómina automática
    
    Args:
        tenant: Tenant específico (opcional)
        
    Returns:
        Dict con resultados del procesamiento
    """
    processor = AutomaticPayrollProcessor()
    return processor.process_fixed_salaries(tenant=tenant)