"""
Utilidades para cálculos de nómina
"""
from decimal import Decimal

def convert_salary_to_period(monthly_salary, frequency):
    """
    Convierte salario mensual a período específico
    """
    if not monthly_salary:
        return Decimal('0.00')
    
    monthly_salary = Decimal(str(monthly_salary))
    
    if frequency == 'daily':
        return monthly_salary / 30  # Aproximado
    elif frequency == 'weekly':
        return monthly_salary / 4
    elif frequency == 'biweekly':
        return monthly_salary / 2
    elif frequency == 'monthly':
        return monthly_salary
    else:
        return monthly_salary / 2  # Default quincenal