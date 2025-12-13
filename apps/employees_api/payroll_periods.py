"""
Sistema de períodos de nómina flexibles
Soporte para diferentes frecuencias de pago
"""
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta, date
from calendar import monthrange
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class PayrollPeriod(models.Model):
    """Modelo para períodos de nómina flexibles"""
    
    FREQUENCY_CHOICES = [
        ('daily', 'Diario'),
        ('weekly', 'Semanal'),
        ('biweekly', 'Quincenal'),
        ('monthly', 'Mensual')
    ]
    
    STATUS_CHOICES = [
        ('open', 'Abierto'),
        ('closed', 'Cerrado'),
        ('paid', 'Pagado')
    ]
    
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='payroll_periods')
    period_type = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    
    # Montos calculados
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Información de pago
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('employee', 'start_date', 'end_date')
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.employee} - {self.period_type} - {self.start_date} to {self.end_date}"


class PayrollPeriodManager:
    """Gestor de períodos de nómina"""
    
    def __init__(self):
        pass
    
    def create_period_for_employee(self, employee, start_date=None, end_date=None):
        """
        Crear período de nómina para un empleado según su frecuencia configurada
        
        Args:
            employee: Instancia del empleado
            start_date: Fecha de inicio (opcional, usa actual)
            end_date: Fecha de fin (opcional, calcula automáticamente)
            
        Returns:
            PayrollPeriod creado
        """
        if not start_date:
            start_date = timezone.now().date()
        
        frequency = getattr(employee, 'payment_frequency', 'biweekly')
        
        if not end_date:
            end_date = self._calculate_period_end_date(start_date, frequency)
        
        period, created = PayrollPeriod.objects.get_or_create(
            employee=employee,
            start_date=start_date,
            end_date=end_date,
            defaults={
                'period_type': frequency,
                'status': 'open'
            }
        )
        
        return period
    
    def get_current_period(self, employee, date=None):
        """
        Obtener período actual para un empleado
        
        Args:
            employee: Instancia del empleado
            date: Fecha de referencia (opcional, usa actual)
            
        Returns:
            PayrollPeriod actual o None
        """
        if not date:
            date = timezone.now().date()
        
        return PayrollPeriod.objects.filter(
            employee=employee,
            start_date__lte=date,
            end_date__gte=date
        ).first()
    
    def get_or_create_current_period(self, employee, date=None):
        """
        Obtener o crear período actual para un empleado
        
        Args:
            employee: Instancia del empleado
            date: Fecha de referencia (opcional, usa actual)
            
        Returns:
            PayrollPeriod actual
        """
        current_period = self.get_current_period(employee, date)
        
        if not current_period:
            if not date:
                date = timezone.now().date()
            
            # Calcular inicio del período según frecuencia
            start_date = self._calculate_period_start_date(date, employee.payment_frequency)
            current_period = self.create_period_for_employee(employee, start_date)
        
        return current_period
    
    def close_period(self, period):
        """
        Cerrar un período de nómina
        
        Args:
            period: PayrollPeriod a cerrar
            
        Returns:
            PayrollPeriod actualizado
        """
        if period.status == 'open':
            period.status = 'closed'
            period.save()
        
        return period
    
    def calculate_period_amount(self, period):
        """
        Calcular montos para un período específico
        
        Args:
            period: PayrollPeriod a calcular
            
        Returns:
            Dict con montos calculados
        """
        employee = period.employee
        
        # Obtener ventas del período
        from apps.pos_api.models import Sale
        sales = Sale.objects.filter(
            employee=employee,
            date_time__date__gte=period.start_date,
            date_time__date__lte=period.end_date,
            status='completed'
        )
        
        total_sales = sum(float(sale.total) for sale in sales)
        
        # Calcular según tipo de empleado
        if employee.salary_type == 'commission':
            gross_amount = Decimal(str(total_sales * float(employee.commission_percentage) / 100))
        elif employee.salary_type == 'fixed':
            gross_amount = self._get_fixed_salary_for_period(employee, period)
        elif employee.salary_type == 'mixed':
            commission = Decimal(str(total_sales * float(employee.commission_percentage) / 100))
            base_salary = self._get_fixed_salary_for_period(employee, period)
            gross_amount = base_salary + commission
        else:
            gross_amount = Decimal('0')
        
        # Calcular descuentos
        from .tax_calculator import DominicanTaxCalculator
        tax_calculator = DominicanTaxCalculator()
        
        # Determinar si aplicar descuentos (solo fin de mes para quincenales)
        should_apply_deductions = self._should_apply_deductions(period)
        deductions = tax_calculator.calculate_deductions(
            gross_amount, 
            employee, 
            should_apply_deductions
        )
        
        net_amount = tax_calculator.get_net_amount(gross_amount, deductions)
        
        return {
            'gross_amount': gross_amount,
            'deductions': deductions,
            'net_amount': net_amount,
            'sales_total': Decimal(str(total_sales)),
            'sales_count': sales.count()
        }
    
    def _calculate_period_end_date(self, start_date, frequency):
        """Calcular fecha de fin según frecuencia"""
        if frequency == 'daily':
            return start_date
        elif frequency == 'weekly':
            return start_date + timedelta(days=6)
        elif frequency == 'biweekly':
            # Lógica quincenal tradicional
            if start_date.day <= 15:
                return start_date.replace(day=15)
            else:
                # Último día del mes
                last_day = monthrange(start_date.year, start_date.month)[1]
                return start_date.replace(day=last_day)
        elif frequency == 'monthly':
            # Último día del mes
            last_day = monthrange(start_date.year, start_date.month)[1]
            return start_date.replace(day=last_day)
        else:
            # Default: quincenal
            return self._calculate_period_end_date(start_date, 'biweekly')
    
    def _calculate_period_start_date(self, date, frequency):
        """Calcular fecha de inicio del período que contiene la fecha dada"""
        if frequency == 'daily':
            return date
        elif frequency == 'weekly':
            # Lunes de la semana
            days_since_monday = date.weekday()
            return date - timedelta(days=days_since_monday)
        elif frequency == 'biweekly':
            # Primera o segunda quincena
            if date.day <= 15:
                return date.replace(day=1)
            else:
                return date.replace(day=16)
        elif frequency == 'monthly':
            return date.replace(day=1)
        else:
            # Default: quincenal
            return self._calculate_period_start_date(date, 'biweekly')
    
    def _get_fixed_salary_for_period(self, employee, period):
        """Obtener salario fijo para el período"""
        monthly_salary = employee.contractual_monthly_salary or Decimal('0')
        
        if period.period_type == 'monthly':
            return monthly_salary
        elif period.period_type == 'biweekly':
            return monthly_salary / 2
        elif period.period_type == 'weekly':
            return monthly_salary / Decimal('4.333')
        elif period.period_type == 'daily':
            return monthly_salary / Decimal('23.83')
        else:
            return monthly_salary / 2  # Default: quincenal
    
    def _should_apply_deductions(self, period):
        """Determinar si aplicar descuentos legales"""
        # Para quincenales: solo en segunda quincena (fin de mes)
        if period.period_type == 'biweekly':
            return period.end_date.day > 15
        
        # Para mensuales: siempre
        if period.period_type == 'monthly':
            return True
        
        # Para otros: no aplicar por defecto
        return False


# Funciones de conveniencia
def get_employee_current_period(employee):
    """Obtener período actual de un empleado"""
    manager = PayrollPeriodManager()
    return manager.get_or_create_current_period(employee)

def calculate_employee_period_pay(employee, period=None):
    """Calcular pago de un empleado para un período"""
    manager = PayrollPeriodManager()
    
    if not period:
        period = manager.get_or_create_current_period(employee)
    
    return manager.calculate_period_amount(period)