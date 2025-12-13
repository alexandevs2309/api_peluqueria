import pytest
from decimal import Decimal
from apps.employees_api.payroll_calculator import (
    calculate_afp, calculate_sfs, calculate_isr_monthly,
    calculate_net_salary, validate_minimum_wage
)

def test_afp_calculation():
    assert calculate_afp(Decimal('15000')) == Decimal('430.50')

def test_sfs_calculation():
    assert calculate_sfs(Decimal('15000')) == Decimal('456.00')

def test_isr_exempt():
    # Salario anual < 416,220 = exento
    assert calculate_isr_monthly(Decimal('30000')) == Decimal('0.00')

def test_isr_first_bracket():
    # Salario anual 600,000 = 15% sobre excedente
    monthly = Decimal('50000')
    isr = calculate_isr_monthly(monthly)
    assert isr > Decimal('0')

def test_net_salary_fortnight():
    gross = Decimal('15000')
    net, deductions = calculate_net_salary(gross, is_fortnight=True)
    assert net == gross - deductions['total']
    assert deductions['afp'] == Decimal('430.50')
    assert deductions['sfs'] == Decimal('456.00')

def test_minimum_wage_validation():
    result = validate_minimum_wage(Decimal('30000'), 'pequena')
    assert result['is_valid'] == True
    assert result['minimum_required'] == Decimal('14161.00')

def test_convert_salary_monthly_to_fortnight():
    """Test conversión mensual a quincenal"""
    from apps.employees_api.payroll_utils import convert_salary_to_period
    
    monthly = Decimal('30000.00')
    fortnight = convert_salary_to_period(monthly, 'biweekly')
    assert fortnight == Decimal('15000.00')

def test_convert_salary_monthly_to_weekly():
    """Test conversión mensual a semanal"""
    from apps.employees_api.payroll_utils import convert_salary_to_period
    
    monthly = Decimal('30000.00')
    weekly = convert_salary_to_period(monthly, 'weekly')
    assert weekly == Decimal('6923.61')  # 30000 / 4.333

def test_period_deductions_from_monthly():
    """Test descuentos calculados desde salario mensual"""
    from apps.employees_api.payroll_calculator import calculate_period_deductions
    
    monthly = Decimal('30000.00')
    deductions = calculate_period_deductions(monthly, 'biweekly')
    
    # Verificar que period_salary es la mitad
    assert deductions['period_salary'] == Decimal('15000.00')
    
    # Verificar descuentos sobre quincenal
    assert deductions['afp'] == Decimal('430.50')  # 2.87% de 15000
    assert deductions['sfs'] == Decimal('456.00')  # 3.04% de 15000
