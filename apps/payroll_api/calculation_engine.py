"""
Servicio de cálculo de nómina - Arquitectura limpia
Reemplaza la lógica en apps/payroll_api/services.py
"""
from decimal import Decimal
from typing import Dict, List, Tuple
from django.db import transaction
from django.utils import timezone
from .models_new import PayrollPeriod, PayrollCalculation, PayrollPayment
from apps.employees_api.earnings_models import Earning
import structlog

logger = structlog.get_logger(__name__)

class PayrollCalculationEngine:
    """
    Motor de cálculo de nómina - Puro, sin efectos secundarios
    """
    
    def __init__(self, employee, period: PayrollPeriod):
        self.employee = employee
        self.period = period
        self.breakdown = {}
    
    def calculate(self) -> Dict:
        """
        Cálculo completo con breakdown auditable
        """
        logger.info("payroll_calculation_started", 
                   employee_id=self.employee.id,
                   period_id=str(self.period.period_id))
        
        # 1. Salario base
        base_salary = self._calculate_base_salary()
        
        # 2. Comisiones
        commission_data = self._calculate_commissions()
        
        # 3. Bonos
        bonuses_data = self._calculate_bonuses()
        
        # 4. Total bruto
        gross_total = base_salary + commission_data['total'] + bonuses_data['total']
        
        # 5. Deducciones
        deductions_data = self._calculate_deductions(gross_total)
        
        # 6. Neto
        net_amount = gross_total - deductions_data['total']
        
        # 7. Construir breakdown completo
        self.breakdown = {
            'calculation_metadata': {
                'employee_id': self.employee.id,
                'period_id': str(self.period.period_id),
                'calculated_at': timezone.now().isoformat(),
                'salary_type': self.employee.salary_type,
                'frequency': self.period.frequency
            },
            'base_salary': {
                'contractual_monthly': str(self.employee.contractual_monthly_salary or 0),
                'period_amount': str(base_salary),
                'calculation_method': self._get_base_salary_method()
            },
            'commissions': commission_data,
            'bonuses': bonuses_data,
            'gross_total': str(gross_total),
            'deductions': deductions_data,
            'net_amount': str(net_amount)
        }
        
        logger.info("payroll_calculation_completed",
                   employee_id=self.employee.id,
                   gross_total=str(gross_total),
                   net_amount=str(net_amount))
        
        return {
            'base_salary': base_salary,
            'commission_total': commission_data['total'],
            'bonuses_total': bonuses_data['total'],
            'gross_total': gross_total,
            'legal_deductions': deductions_data['legal'],
            'loan_deductions': deductions_data['loans'],
            'other_deductions': deductions_data['other'],
            'total_deductions': deductions_data['total'],
            'net_amount': net_amount,
            'breakdown': self.breakdown
        }
    
    def _calculate_base_salary(self) -> Decimal:
        """Cálculo de salario base según tipo y frecuencia"""
        if self.employee.salary_type not in ['fixed', 'mixed']:
            return Decimal('0.00')
        
        monthly_salary = self.employee.contractual_monthly_salary or Decimal('0.00')
        
        if self.period.frequency == 'biweekly':
            return monthly_salary / 2
        elif self.period.frequency == 'weekly':
            return monthly_salary / 4
        elif self.period.frequency == 'daily':
            return monthly_salary / 30
        else:  # monthly
            return monthly_salary
    
    def _calculate_commissions(self) -> Dict:
        """Cálculo detallado de comisiones"""
        if self.employee.salary_type not in ['commission', 'mixed']:
            return {'total': Decimal('0.00'), 'details': []}
        
        commission_rate = (self.employee.commission_percentage or Decimal('0.00')) / 100
        
        # Obtener earnings del período
        earnings = Earning.objects.filter(
            employee=self.employee,
            date_earned__date__gte=self.period.period_start,
            date_earned__date__lte=self.period.period_end
        ).select_related('sale')
        
        commission_details = []
        total_commission = Decimal('0.00')
        
        for earning in earnings:
            commission_amount = earning.amount * commission_rate
            total_commission += commission_amount
            
            commission_details.append({
                'earning_id': earning.id,
                'sale_id': getattr(earning.sale, 'id', None),
                'service_name': earning.service_name or 'Unknown',
                'earning_amount': str(earning.amount),
                'commission_rate': str(self.employee.commission_percentage),
                'commission_amount': str(commission_amount),
                'date': earning.date_earned.isoformat()
            })
        
        return {
            'total': total_commission,
            'rate_percentage': str(self.employee.commission_percentage or 0),
            'total_earnings': str(sum(e.amount for e in earnings)),
            'details': commission_details
        }
    
    def _calculate_bonuses(self) -> Dict:
        """Cálculo de bonos (extensible)"""
        # Por ahora sin bonos, pero estructura preparada
        return {
            'total': Decimal('0.00'),
            'details': []
        }
    
    def _calculate_deductions(self, gross_amount: Decimal) -> Dict:
        """Cálculo completo de deducciones"""
        legal_deductions = self._calculate_legal_deductions(gross_amount)
        loan_deductions = self._calculate_loan_deductions()
        other_deductions = Decimal('0.00')  # Extensible
        
        total = legal_deductions + loan_deductions + other_deductions
        
        return {
            'legal': legal_deductions,
            'loans': loan_deductions,
            'other': other_deductions,
            'total': total,
            'details': {
                'legal_breakdown': self._get_legal_deductions_breakdown(gross_amount),
                'loan_breakdown': self._get_loan_deductions_breakdown()
            }
        }
    
    def _calculate_legal_deductions(self, gross_amount: Decimal) -> Decimal:
        """Deducciones legales según normativa RD"""
        if not any([self.employee.apply_afp, self.employee.apply_sfs, self.employee.apply_isr]):
            return Decimal('0.00')
        
        # Solo aplicar en última quincena del mes
        if not self._is_last_fortnight_of_month():
            return Decimal('0.00')
        
        total_deductions = Decimal('0.00')
        
        if self.employee.apply_afp:
            total_deductions += gross_amount * Decimal('0.0287')  # 2.87%
        
        if self.employee.apply_sfs:
            total_deductions += gross_amount * Decimal('0.0304')  # 3.04%
        
        # ISR es más complejo, por ahora básico
        if self.employee.apply_isr:
            total_deductions += gross_amount * Decimal('0.15')  # 15% simplificado
        
        return total_deductions
    
    def _calculate_loan_deductions(self) -> Decimal:
        """Deducciones de préstamos activos"""
        from apps.employees_api.advance_loans import AdvanceLoan
        
        active_loans = AdvanceLoan.objects.filter(
            employee=self.employee,
            status='active',
            remaining_balance__gt=0
        )
        
        return sum(loan.monthly_payment for loan in active_loans)
    
    def _get_base_salary_method(self) -> str:
        """Descripción del método de cálculo de salario base"""
        if self.employee.salary_type == 'fixed':
            return f"Fixed salary - {self.period.frequency}"
        elif self.employee.salary_type == 'mixed':
            return f"Mixed salary (base component) - {self.period.frequency}"
        return "No base salary"
    
    def _is_last_fortnight_of_month(self) -> bool:
        """Determina si es la última quincena del mes"""
        if self.period.frequency != 'biweekly':
            return True  # Para otros períodos, siempre aplicar
        
        return self.period.period_end.day > 15
    
    def _get_legal_deductions_breakdown(self, gross_amount: Decimal) -> Dict:
        """Breakdown detallado de deducciones legales"""
        breakdown = {}
        
        if self.employee.apply_afp:
            breakdown['afp'] = {
                'rate': '2.87%',
                'amount': str(gross_amount * Decimal('0.0287'))
            }
        
        if self.employee.apply_sfs:
            breakdown['sfs'] = {
                'rate': '3.04%',
                'amount': str(gross_amount * Decimal('0.0304'))
            }
        
        if self.employee.apply_isr:
            breakdown['isr'] = {
                'rate': '15.00%',
                'amount': str(gross_amount * Decimal('0.15'))
            }
        
        return breakdown
    
    def _get_loan_deductions_breakdown(self) -> List[Dict]:
        """Breakdown detallado de deducciones de préstamos"""
        from apps.employees_api.advance_loans import AdvanceLoan
        
        active_loans = AdvanceLoan.objects.filter(
            employee=self.employee,
            status='active',
            remaining_balance__gt=0
        )
        
        return [
            {
                'loan_id': loan.id,
                'monthly_payment': str(loan.monthly_payment),
                'remaining_balance': str(loan.remaining_balance),
                'request_date': loan.request_date.isoformat()
            }
            for loan in active_loans
        ]

class PayrollService:
    """
    Servicio de orquestación de nómina
    """
    
    @classmethod
    @transaction.atomic
    def calculate_payroll(cls, employee, period: PayrollPeriod, calculated_by=None) -> PayrollCalculation:
        """
        Calcula y persiste nómina con versionado
        """
        # 1. Ejecutar cálculo
        engine = PayrollCalculationEngine(employee, period)
        calculation_result = engine.calculate()
        
        # 2. Determinar nueva versión
        last_version = PayrollCalculation.objects.filter(
            employee=employee,
            period=period
        ).aggregate(max_version=models.Max('version'))['max_version'] or 0
        
        new_version = last_version + 1
        
        # 3. Crear registro de cálculo
        calculation = PayrollCalculation.objects.create(
            employee=employee,
            period=period,
            tenant=employee.tenant,
            version=new_version,
            is_current=True,
            calculation_breakdown=calculation_result['breakdown'],
            base_salary=calculation_result['base_salary'],
            commission_total=calculation_result['commission_total'],
            bonuses_total=calculation_result['bonuses_total'],
            gross_total=calculation_result['gross_total'],
            legal_deductions=calculation_result['legal_deductions'],
            loan_deductions=calculation_result['loan_deductions'],
            other_deductions=calculation_result['other_deductions'],
            total_deductions=calculation_result['total_deductions'],
            net_amount=calculation_result['net_amount'],
            calculated_by=calculated_by
        )
        
        logger.info("payroll_calculation_persisted",
                   calculation_id=str(calculation.calculation_id),
                   employee_id=employee.id,
                   version=new_version)
        
        return calculation
    
    @classmethod
    @transaction.atomic
    def execute_payment(cls, calculation: PayrollCalculation, paid_by=None, **payment_kwargs) -> PayrollPayment:
        """
        Ejecuta pago basado en cálculo
        """
        if hasattr(calculation, 'payment'):
            raise ValueError("Payment already executed for this calculation")
        
        payment = PayrollPayment.objects.create(
            calculation=calculation,
            tenant=calculation.tenant,
            amount_paid=calculation.net_amount,
            paid_by=paid_by,
            **payment_kwargs
        )
        
        logger.info("payroll_payment_executed",
                   payment_id=str(payment.payment_id),
                   calculation_id=str(calculation.calculation_id),
                   amount=str(payment.amount_paid))
        
        return payment