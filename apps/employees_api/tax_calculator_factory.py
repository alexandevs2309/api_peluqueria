"""
Factory para calculadoras de impuestos por país - DEPRECATED
Usar tax_calculators.py directamente
"""
from .tax_calculators import TaxCalculatorFactory as NewFactory

# Mantener compatibilidad hacia atrás
class TaxCalculatorFactory:
    @staticmethod
    def get_calculator(country_code: str = 'DO'):
        return NewFactory.get_calculator(country_code)
    
    @staticmethod
    def get_supported_countries():
        return NewFactory.get_supported_countries()
    
    @staticmethod
    def get_all_countries():
        return NewFactory.get_country_tax_info()