"""
Calculadoras de impuestos centralizadas por país
"""
from decimal import Decimal
from typing import Dict, Any

class BaseTaxCalculator:
    """Clase base para calculadoras de impuestos"""
    
    def calculate_deductions(self, gross_amount: Decimal, employee: Any, is_month_end: bool = False) -> Dict[str, Decimal]:
        raise NotImplementedError
    
    def get_net_amount(self, gross_amount: Decimal, deductions: Dict[str, Decimal]) -> Decimal:
        return gross_amount - deductions.get('total', Decimal('0'))
    
    def is_month_end_payment(self, year: int, fortnight: int) -> bool:
        return False

class DominicanTaxCalculator(BaseTaxCalculator):
    """República Dominicana - AFP, SFS, ISR"""
    
    AFP_RATE = Decimal('0.0287')  # 2.87%
    SFS_RATE = Decimal('0.0304')  # 3.04%
    
    ISR_BRACKETS = [
        (Decimal('416220'), Decimal('0')),
        (Decimal('624329'), Decimal('0.15')),
        (Decimal('867123'), Decimal('0.20')),
        (float('inf'), Decimal('0.25'))
    ]
    
    def calculate_deductions(self, gross_amount: Decimal, employee: Any, is_month_end: bool = False) -> Dict[str, Decimal]:
        deductions = {'afp': Decimal('0'), 'sfs': Decimal('0'), 'isr': Decimal('0'), 'total': Decimal('0')}
        
        if not is_month_end:
            return deductions
        
        if getattr(employee, 'apply_afp', False):
            deductions['afp'] = gross_amount * self.AFP_RATE
        if getattr(employee, 'apply_sfs', False):
            deductions['sfs'] = gross_amount * self.SFS_RATE
        if getattr(employee, 'apply_isr', False):
            deductions['isr'] = self._calculate_isr(gross_amount)
        
        deductions['total'] = sum([deductions['afp'], deductions['sfs'], deductions['isr']])
        return deductions
    
    def _calculate_isr(self, monthly_gross: Decimal) -> Decimal:
        if monthly_gross <= self.ISR_BRACKETS[0][0]:
            return Decimal('0')
        
        isr_amount = Decimal('0')
        remaining_amount = monthly_gross
        previous_limit = Decimal('0')
        
        for limit, rate in self.ISR_BRACKETS:
            if remaining_amount <= 0:
                break
            taxable_in_bracket = min(remaining_amount, limit - previous_limit)
            isr_amount += taxable_in_bracket * rate
            remaining_amount -= taxable_in_bracket
            previous_limit = limit
            if limit == float('inf'):
                break
        
        return isr_amount
    
    def is_month_end_payment(self, year: int, fortnight: int) -> bool:
        return fortnight % 2 == 0

class USATaxCalculator(BaseTaxCalculator):
    """Estados Unidos - Sin descuentos obligatorios"""
    
    def calculate_deductions(self, gross_amount: Decimal, employee: Any, is_month_end: bool = False) -> Dict[str, Decimal]:
        return {'federal_tax': Decimal('0'), 'state_tax': Decimal('0'), 'total': Decimal('0')}

class MexicoTaxCalculator(BaseTaxCalculator):
    """México - IMSS, INFONAVIT"""
    
    IMSS_RATE = Decimal('0.0250')
    INFONAVIT_RATE = Decimal('0.05')
    UMA_MONTHLY = Decimal('108.57') * 30
    
    def calculate_deductions(self, gross_amount: Decimal, employee: Any, is_month_end: bool = False) -> Dict[str, Decimal]:
        deductions = {'imss': Decimal('0'), 'infonavit': Decimal('0'), 'isr': Decimal('0'), 'total': Decimal('0')}
        
        if not getattr(employee, 'apply_mexican_taxes', False):
            return deductions
        
        if gross_amount > 0:
            deductions['imss'] = gross_amount * self.IMSS_RATE
        
        if gross_amount > self.UMA_MONTHLY and getattr(employee, 'apply_infonavit', False):
            deductions['infonavit'] = gross_amount * self.INFONAVIT_RATE
        
        deductions['total'] = deductions['imss'] + deductions['infonavit']
        return deductions
    
    def is_month_end_payment(self, year: int, fortnight: int) -> bool:
        return True

class ColombiaTaxCalculator(BaseTaxCalculator):
    """Colombia - Salud, Pensión"""
    
    SALUD_RATE = Decimal('0.04')
    PENSION_RATE = Decimal('0.04')
    SMMLV_2024 = Decimal('1300000')
    
    def calculate_deductions(self, gross_amount: Decimal, employee: Any, is_month_end: bool = False) -> Dict[str, Decimal]:
        deductions = {'salud': Decimal('0'), 'pension': Decimal('0'), 'retencion': Decimal('0'), 'total': Decimal('0')}
        
        if not getattr(employee, 'apply_colombian_taxes', False):
            return deductions
        
        if gross_amount >= self.SMMLV_2024:
            deductions['salud'] = gross_amount * self.SALUD_RATE
            deductions['pension'] = gross_amount * self.PENSION_RATE
        
        deductions['total'] = deductions['salud'] + deductions['pension']
        return deductions
    
    def is_month_end_payment(self, year: int, fortnight: int) -> bool:
        return True

class NoTaxCalculator(BaseTaxCalculator):
    """Sin descuentos legales"""
    
    def calculate_deductions(self, gross_amount: Decimal, employee: Any, is_month_end: bool = False) -> Dict[str, Decimal]:
        return {'total': Decimal('0')}

class TaxCalculatorFactory:
    """Factory centralizada para calculadoras"""
    
    CALCULATORS = {
        'DO': DominicanTaxCalculator,
        'US': USATaxCalculator,
        'MX': MexicoTaxCalculator,
        'CO': ColombiaTaxCalculator
    }
    
    @staticmethod
    def get_calculator(country_code: str = 'DO'):
        calculator_class = TaxCalculatorFactory.CALCULATORS.get(country_code, NoTaxCalculator)
        return calculator_class()
    
    @staticmethod
    def get_supported_countries():
        return {
            'DO': 'República Dominicana',
            'US': 'Estados Unidos',
            'MX': 'México',
            'CO': 'Colombia'
        }
    
    @staticmethod
    def get_country_tax_info():
        return {
            'DO': {'name': 'República Dominicana', 'taxes': ['AFP (2.87%)', 'SFS (3.04%)', 'ISR (Progresivo)']},
            'US': {'name': 'Estados Unidos', 'taxes': ['Sin descuentos obligatorios']},
            'MX': {'name': 'México', 'taxes': ['IMSS (2.5%)', 'INFONAVIT (5%)']},
            'CO': {'name': 'Colombia', 'taxes': ['Salud (4%)', 'Pensión (4%)']}
        }