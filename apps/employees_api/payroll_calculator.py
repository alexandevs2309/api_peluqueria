"""
Calculadora de nómina según normativa laboral de República Dominicana
"""
from decimal import Decimal
from typing import Dict, Tuple
from .payroll_utils import convert_salary_to_period

# Constantes según normativa dominicana
SALARIO_MINIMO = {
    'grande': Decimal('24990.00'),      # Empresa grande
    'mediana': Decimal('22907.00'),     # Empresa mediana
    'pequena': Decimal('14161.00'),     # Empresa pequeña
    'micro': Decimal('13685.00')        # Microempresa
}

# Descuentos obligatorios (porcentajes)
AFP_RATE = Decimal('2.87')              # 2.87%
SFS_RATE = Decimal('3.04')              # 3.04%

# Escalas ISR (Impuesto Sobre la Renta) - Anual
ISR_SCALES = [
    (Decimal('0'), Decimal('416220.00'), Decimal('0')),           # Exento
    (Decimal('416220.01'), Decimal('624329.00'), Decimal('15')), # 15%
    (Decimal('624329.01'), Decimal('867123.00'), Decimal('20')), # 20%
    (Decimal('867123.01'), Decimal('999999999'), Decimal('25'))  # 25%
]


def calculate_afp(gross_salary: Decimal) -> Decimal:
    """Calcula descuento AFP (2.87%)"""
    return (gross_salary * AFP_RATE / Decimal('100')).quantize(Decimal('0.01'))


def calculate_sfs(gross_salary: Decimal) -> Decimal:
    """Calcula descuento SFS (3.04%)"""
    return (gross_salary * SFS_RATE / Decimal('100')).quantize(Decimal('0.01'))


def calculate_isr_monthly(monthly_salary: Decimal) -> Decimal:
    """
    Calcula ISR mensual basado en salario anual proyectado
    ISR se aplica solo si salario anual > RD$ 416,220
    """
    annual_salary = monthly_salary * Decimal('12')
    
    # Buscar escala aplicable
    for min_val, max_val, rate in ISR_SCALES:
        if min_val <= annual_salary <= max_val:
            if rate == Decimal('0'):
                return Decimal('0.00')
            
            # Calcular ISR anual y dividir entre 12
            taxable_amount = annual_salary - Decimal('416220.00')
            annual_isr = (taxable_amount * rate / Decimal('100'))
            monthly_isr = (annual_isr / Decimal('12')).quantize(Decimal('0.01'))
            return monthly_isr
    
    return Decimal('0.00')


def calculate_period_deductions(
    contractual_monthly_salary: Decimal,
    payment_frequency: str = 'biweekly'
) -> Dict[str, Decimal]:
    """
    Calcula descuentos para cualquier período de pago.
    
    Args:
        contractual_monthly_salary: Salario mensual contractual
        payment_frequency: Frecuencia de pago
        
    Returns:
        Dict con AFP, SFS, ISR y total de descuentos
    """
    # Convertir a monto del período
    period_salary = convert_salary_to_period(contractual_monthly_salary, payment_frequency)
    
    # Calcular descuentos sobre salario del período
    afp = calculate_afp(period_salary)
    sfs = calculate_sfs(period_salary)
    
    # ISR siempre se calcula sobre base mensual
    isr_monthly = calculate_isr_monthly(contractual_monthly_salary)
    
    # Prorratear ISR según frecuencia
    if payment_frequency == 'monthly':
        isr = isr_monthly
    elif payment_frequency == 'biweekly':
        isr = (isr_monthly / Decimal('2')).quantize(Decimal('0.01'))
    elif payment_frequency == 'weekly':
        isr = (isr_monthly / Decimal('4.333')).quantize(Decimal('0.01'))
    elif payment_frequency == 'daily':
        isr = (isr_monthly / Decimal('23.83')).quantize(Decimal('0.01'))
    else:
        isr = (isr_monthly / Decimal('2')).quantize(Decimal('0.01'))
    
    total_deductions = afp + sfs + isr
    
    return {
        'afp': afp,
        'sfs': sfs,
        'isr': isr,
        'total': total_deductions,
        'period_salary': period_salary
    }


def calculate_fortnight_deductions(fortnight_salary: Decimal) -> Dict[str, Decimal]:
    """[DEPRECATED] Usar calculate_period_deductions con contractual_monthly_salary"""
    monthly_salary = fortnight_salary * Decimal('2')
    result = calculate_period_deductions(monthly_salary, 'biweekly')
    # Remover period_salary para mantener backward compatibility
    result.pop('period_salary', None)
    return result


def calculate_net_salary(
    gross_salary: Decimal, 
    is_fortnight: bool = True,
    apply_afp: bool = True,
    apply_sfs: bool = True,
    apply_isr: bool = True
) -> Tuple[Decimal, Dict[str, Decimal]]:
    """
    Calcula salario neto después de descuentos
    
    Args:
        gross_salary: Salario bruto (quincenal o mensual)
        is_fortnight: True si es quincenal, False si es mensual
        apply_afp: Aplicar descuento AFP
        apply_sfs: Aplicar descuento SFS
        apply_isr: Aplicar descuento ISR
        
    Returns:
        Tuple (salario_neto, desglose_descuentos)
    """
    if is_fortnight:
        deductions = calculate_fortnight_deductions(gross_salary)
    else:
        # Si es mensual, calcular directamente
        afp = calculate_afp(gross_salary) if apply_afp else Decimal('0')
        sfs = calculate_sfs(gross_salary) if apply_sfs else Decimal('0')
        isr = calculate_isr_monthly(gross_salary) if apply_isr else Decimal('0')
        deductions = {
            'afp': afp,
            'sfs': sfs,
            'isr': isr,
            'total': afp + sfs + isr
        }
    
    # Aplicar solo los descuentos habilitados
    if not apply_afp:
        deductions['afp'] = Decimal('0')
    if not apply_sfs:
        deductions['sfs'] = Decimal('0')
    if not apply_isr:
        deductions['isr'] = Decimal('0')
    
    deductions['total'] = deductions['afp'] + deductions['sfs'] + deductions['isr']
    net_salary = gross_salary - deductions['total']
    return net_salary, deductions


def validate_minimum_wage(monthly_salary: Decimal, company_size: str = 'pequena') -> Dict[str, any]:
    """
    Valida si el salario cumple con el mínimo legal
    
    Args:
        monthly_salary: Salario mensual
        company_size: 'grande', 'mediana', 'pequena', 'micro'
        
    Returns:
        Dict con validación y detalles
    """
    minimum = SALARIO_MINIMO.get(company_size, SALARIO_MINIMO['pequena'])
    is_valid = monthly_salary >= minimum
    
    return {
        'is_valid': is_valid,
        'monthly_salary': monthly_salary,
        'minimum_required': minimum,
        'company_size': company_size,
        'difference': monthly_salary - minimum
    }


def calculate_regalia_pascual(annual_salary: Decimal) -> Decimal:
    """
    Calcula Regalía Pascual (1/12 del salario anual)
    """
    return (annual_salary / Decimal('12')).quantize(Decimal('0.01'))


def calculate_overtime_pay(hourly_rate: Decimal, overtime_hours: Decimal) -> Decimal:
    """
    Calcula pago de horas extras (135% del salario por hora)
    """
    overtime_rate = hourly_rate * Decimal('1.35')
    return (overtime_rate * overtime_hours).quantize(Decimal('0.01'))


def get_payroll_summary(gross_salary: Decimal, is_fortnight: bool = True) -> Dict[str, any]:
    """
    Genera resumen completo de nómina
    
    Returns:
        Dict con todos los cálculos y desglose
    """
    net_salary, deductions = calculate_net_salary(gross_salary, is_fortnight)
    
    # Proyectar a mensual si es quincenal
    monthly_gross = gross_salary * Decimal('2') if is_fortnight else gross_salary
    
    # Validar salario mínimo
    validation = validate_minimum_wage(monthly_gross)
    
    return {
        'gross_salary': gross_salary,
        'period_type': 'quincenal' if is_fortnight else 'mensual',
        'deductions': {
            'afp': deductions['afp'],
            'sfs': deductions['sfs'],
            'isr': deductions['isr'],
            'total': deductions['total']
        },
        'net_salary': net_salary,
        'monthly_projection': monthly_gross,
        'minimum_wage_validation': validation,
        'annual_projection': monthly_gross * Decimal('12'),
        'regalia_pascual': calculate_regalia_pascual(monthly_gross * Decimal('12'))
    }
