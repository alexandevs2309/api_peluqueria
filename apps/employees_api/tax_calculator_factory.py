"""
Factory para calculadoras de impuestos por país
"""
from .tax_calculator import DominicanTaxCalculator

class TaxCalculatorFactory:
    """Factory para obtener calculadora de impuestos según país"""
    
    @staticmethod
    def get_calculator(country_code: str = 'DO'):
        """
        Obtiene calculadora de impuestos según código de país
        
        Args:
            country_code: Código ISO del país (ej: 'DO', 'US', 'MX')
            
        Returns:
            Instancia de calculadora de impuestos
        """
        if country_code == 'DO':
            return DominicanTaxCalculator()
        
        # Para países no soportados: sin descuentos legales
        from .tax_calculator import NoTaxCalculator
        return NoTaxCalculator()
    
    @staticmethod
    def get_supported_countries():
        """Retorna países con reglas fiscales implementadas"""
        return {
            'DO': 'República Dominicana'
        }
    
    @staticmethod
    def get_all_countries():
        """Retorna todos los países (soportados + sin descuentos)"""
        return {
            'DO': 'República Dominicana (Completo)',
            'US': 'Estados Unidos (Sin descuentos legales)',
            'MX': 'México (Sin descuentos legales)',
            'CO': 'Colombia (Sin descuentos legales)',
            'ES': 'España (Sin descuentos legales)'
        }