from decimal import Decimal
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from .models import PayrollSettlement, SettlementEarning
from apps.employees_api.earnings_models import Earning
from apps.employees_api.advance_loans import AdvanceLoan

class PayrollSettlementService:
    """
    Servicio de liquidación de nómina
    Calcula montos sin ejecutar pagos
    """
    
    @classmethod
    def mark_as_paid(cls, settlement):
        """
        Marcar settlement como pagado
        """
        settlement.status = 'PAID'
        settlement.save()
        return settlement
    
    def calculate_settlement(self, settlement):
        """
        Calcula liquidación completa para un settlement
        """
        with transaction.atomic():
            # 1. Calcular salario fijo prorrateado
            fixed_amount = self._calculate_fixed_salary(settlement)
            
            # 2. Agregar earnings por período
            commission_amount = self._calculate_commission(settlement)
            
            # 3. Calcular total bruto
            gross_amount = fixed_amount + commission_amount
            
            # 4. Calcular deducciones (préstamos + legales)
            loan_deductions = self._calculate_loan_deductions(settlement)
            afp_deduction, sfs_deduction, isr_deduction = self._calculate_legal_deductions(settlement, gross_amount)
            total_deductions = loan_deductions + afp_deduction + sfs_deduction + isr_deduction
            
            # 5. Calcular neto
            net_amount = gross_amount - total_deductions
            
            # 6. Actualizar settlement
            settlement.fixed_salary_amount = fixed_amount
            settlement.commission_amount = commission_amount
            settlement.gross_amount = gross_amount
            settlement.afp_deduction = afp_deduction
            settlement.sfs_deduction = sfs_deduction
            settlement.isr_deduction = isr_deduction
            settlement.total_deductions = total_deductions
            settlement.net_amount = net_amount
            settlement.save()
            
            return settlement
    
    def _calculate_fixed_salary(self, settlement):
        """
        Calcula salario fijo prorrateado según período
        """
        employee = settlement.employee
        
        if employee.salary_type not in ['fixed', 'mixed']:
            return Decimal('0.00')
        
        base_salary = employee.contractual_monthly_salary or Decimal('0.00')
        
        # Si es período quincenal completo
        if settlement.frequency == 'biweekly':
            # Convertir salario mensual a quincenal
            base_salary = base_salary / 2
            period_days = (settlement.period_end - settlement.period_start).days + 1
            
            # Verificar si es quincena completa
            if self._is_full_fortnight(settlement.period_start, settlement.period_end):
                return base_salary
            else:
                # Prorratear por días
                fortnight_days = self._get_fortnight_days(settlement.period_start)
                daily_salary = base_salary / fortnight_days
                return daily_salary * period_days
        
        return base_salary
    
    def _calculate_commission(self, settlement):
        """
        Calcula comisiones basadas en earnings del período
        """
        employee = settlement.employee
        
        if employee.salary_type not in ['commission', 'mixed']:
            return Decimal('0.00')
        
        commission_rate = (employee.commission_percentage or Decimal('0.00')) / 100
        
        # Obtener earnings del período
        earnings = Earning.objects.filter(
            employee=employee,
            date_earned__date__gte=settlement.period_start,
            date_earned__date__lte=settlement.period_end
        )
        
        total_earnings = sum(earning.amount for earning in earnings)
        commission_amount = total_earnings * commission_rate
        
        # Crear relaciones de trazabilidad
        for earning in earnings:
            SettlementEarning.objects.get_or_create(
                settlement=settlement,
                earning=earning,
                defaults={
                    'earning_amount': earning.amount,
                    'commission_rate': employee.commission_percentage or Decimal('0.00'),
                    'commission_amount': earning.amount * commission_rate
                }
            )
        
        return commission_amount
    
    def _calculate_loan_deductions(self, settlement):
        """
        Calcula deducciones de préstamos activos
        """
        employee = settlement.employee
        
        # Obtener préstamos activos ordenados por fecha (FIFO)
        active_loans = AdvanceLoan.objects.filter(
            employee=employee,
            status='active',
            remaining_balance__gt=0
        ).order_by('request_date')
        
        total_loan_deductions = Decimal('0.00')
        
        for loan in active_loans:
            # Deducción = min(cuota mensual, saldo restante)
            deduction = min(loan.monthly_payment, loan.remaining_balance)
            total_loan_deductions += deduction
        
        return total_loan_deductions
    
    def _calculate_legal_deductions(self, settlement, gross_amount):
        """
        Calcula descuentos legales (AFP, SFS, ISR)
        Retorna tupla (afp, sfs, isr)
        """
        employee = settlement.employee
        
        afp_deduction = Decimal('0.00')
        sfs_deduction = Decimal('0.00')
        isr_deduction = Decimal('0.00')
        
        if employee.apply_afp:
            afp_deduction = gross_amount * Decimal('0.0287')  # 2.87%
        
        if employee.apply_sfs:
            sfs_deduction = gross_amount * Decimal('0.0304')  # 3.04%
        
        if employee.apply_isr:
            # ISR simplificado - solo si supera umbral
            if gross_amount > Decimal('34685'):  # Umbral mensual 2024
                isr_deduction = gross_amount * Decimal('0.15')  # 15%
        
        return afp_deduction, sfs_deduction, isr_deduction
    
    def _is_full_fortnight(self, start_date, end_date):
        """
        Verifica si el período es una quincena completa
        """
        # Primera quincena: 1-15
        if start_date.day == 1 and end_date.day == 15:
            return True
        
        # Segunda quincena: 16-último día del mes
        if start_date.day == 16:
            # Calcular último día del mes
            if start_date.month == 12:
                next_month = start_date.replace(year=start_date.year + 1, month=1, day=1)
            else:
                next_month = start_date.replace(month=start_date.month + 1, day=1)
            last_day = (next_month - timedelta(days=1)).day
            
            if end_date.day == last_day:
                return True
        
        return False
    
    def _get_fortnight_days(self, date):
        """
        Obtiene el número de días en la quincena
        """
        if date.day <= 15:
            return 15  # Primera quincena
        else:
            # Segunda quincena: calcular días hasta fin de mes
            if date.month == 12:
                next_month = date.replace(year=date.year + 1, month=1, day=1)
            else:
                next_month = date.replace(month=date.month + 1, day=1)
            last_day = (next_month - timedelta(days=1)).day
            return last_day - 15  # días de la segunda quincena