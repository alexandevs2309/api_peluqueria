"""
Calculadora sin descuentos legales para países no soportados
"""
from decimal import Decimal
from typing import Dict, Any

class NoTaxCalculator:
    """Calculadora que no aplica descuentos legales"""
    
    def calculate_deductions(self, gross_amount: Decimal, employee: Any, is_month_end: bool = False) -> Dict[str, Decimal]:
        """
        No aplica descuentos legales
        
        Returns:
            Dict con descuentos en cero
        """
        return {
            'afp': Decimal('0'),
            'sfs': Decimal('0'),
            'isr': Decimal('0'),
            'total': Decimal('0')
        }
    
    def get_net_amount(self, gross_amount: Decimal, deductions: Dict[str, Decimal]) -> Decimal:
        """Retorna monto bruto sin descuentos"""
        return gross_amount
    
    def is_month_end_payment(self, year: int, fortnight: int) -> bool:
        """Siempre retorna False (sin descuentos)"""
        return False