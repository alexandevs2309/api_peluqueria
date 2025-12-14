"""
Calculadora de descuentos legales para República Dominicana
"""
from decimal import Decimal
from typing import Dict, Any

# Importar calculadora sin descuentos
from .no_tax_calculator import NoTaxCalculator

class DominicanTaxCalculator:
    """Calculadora de impuestos y descuentos según ley dominicana"""
    
    # Tasas oficiales República Dominicana 2024
    AFP_RATE = Decimal('0.0287')  # 2.87%
    SFS_RATE = Decimal('0.0304')  # 3.04%
    
    # Escala ISR mensual (RD$)
    ISR_BRACKETS = [
        (Decimal('416220'), Decimal('0')),      # Hasta 416,220 - 0%
        (Decimal('624329'), Decimal('0.15')),   # 416,221 - 624,329 - 15%
        (Decimal('867123'), Decimal('0.20')),   # 624,330 - 867,123 - 20%
        (float('inf'), Decimal('0.25'))         # Más de 867,123 - 25%
    ]
    
    def __init__(self):
        pass
    
    def calculate_deductions(self, gross_amount: Decimal, employee: Any, is_month_end: bool = False) -> Dict[str, Decimal]:
        """
        Calcula todos los descuentos legales
        
        Args:
            gross_amount: Monto bruto a pagar
            employee: Instancia del empleado
            is_month_end: Si es fin de mes (para aplicar descuentos)
        
        Returns:
            Dict con descuentos calculados
        """
        deductions = {
            'afp': Decimal('0'),
            'sfs': Decimal('0'),
            'isr': Decimal('0'),
            'total': Decimal('0')
        }
        
        # Solo aplicar descuentos en fin de mes
        if not is_month_end:
            return deductions
        
        # AFP - Administradora de Fondos de Pensiones
        if getattr(employee, 'apply_afp', False):
            deductions['afp'] = gross_amount * self.AFP_RATE
        
        # SFS - Seguro Familiar de Salud
        if getattr(employee, 'apply_sfs', False):
            deductions['sfs'] = gross_amount * self.SFS_RATE
        
        # ISR - Impuesto Sobre la Renta
        if getattr(employee, 'apply_isr', False):
            deductions['isr'] = self._calculate_isr(gross_amount)
        
        # Total de descuentos
        deductions['total'] = sum([
            deductions['afp'],
            deductions['sfs'], 
            deductions['isr']
        ])
        
        return deductions
    
    def _calculate_isr(self, monthly_gross: Decimal) -> Decimal:
        """
        Calcula ISR según escala progresiva dominicana
        
        Args:
            monthly_gross: Salario bruto mensual
            
        Returns:
            Monto de ISR a descontar
        """
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
    
    def get_net_amount(self, gross_amount: Decimal, deductions: Dict[str, Decimal]) -> Decimal:
        """
        Calcula monto neto después de descuentos
        
        Args:
            gross_amount: Monto bruto
            deductions: Descuentos calculados
            
        Returns:
            Monto neto a pagar
        """
        return gross_amount - deductions['total']
    
    def is_month_end_payment(self, year: int, fortnight: int) -> bool:
        """
        Determina si es pago de fin de mes (quincenas pares)
        
        Args:
            year: Año del pago
            fortnight: Número de quincena (1-24)
            
        Returns:
            True si es fin de mes
        """
        return fortnight % 2 == 0