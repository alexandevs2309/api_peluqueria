from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.models import Q

class SettingsGovernor:
    """Gobierno defensivo para configuraciones críticas"""
    
    # ZONA ROJA - Configuraciones críticas que afectan lógica financiera
    CRITICAL_SETTINGS = {
        'currency': {
            'impact': 'Afecta todos los cálculos financieros en POS, Pagos y Reportes',
            'validation': lambda value: value in ['COP', 'USD', 'EUR', 'DOP'],
            'requires_confirmation': True
        },
        'currency_symbol': {
            'impact': 'Afecta la visualización de montos en todo el sistema',
            'validation': lambda value: len(value) <= 5,
            'requires_confirmation': True
        },
        'default_commission_rate': {
            'impact': 'Afecta el cálculo de comisiones para nuevos empleados',
            'validation': lambda value: 0 <= float(value) <= 100,
            'requires_confirmation': True
        },
        'default_fixed_salary': {
            'impact': 'Afecta el salario base para nuevos empleados',
            'validation': lambda value: float(value) >= 0,
            'requires_confirmation': True
        },
        'tax_rate': {
            'impact': 'Afecta cálculos de impuestos en POS y facturación',
            'validation': lambda value: 0 <= float(value) <= 100,
            'requires_confirmation': True
        }
    }
    
    # ZONA AMARILLA - Configuraciones sensibles
    SENSITIVE_SETTINGS = {
        'service_discount_limit': {
            'impact': 'Afecta el descuento máximo permitido en servicios',
            'validation': lambda value: 0 <= float(value) <= 100,
            'requires_confirmation': False
        },
        'cancellation_policy_hours': {
            'impact': 'Afecta la política de cancelación de citas',
            'validation': lambda value: int(value) >= 0,
            'requires_confirmation': False
        },
        'booking_advance_days': {
            'impact': 'Afecta cuántos días pueden reservar los clientes',
            'validation': lambda value: 1 <= int(value) <= 365,
            'requires_confirmation': False
        }
    }
    
    # ZONA VERDE - Configuraciones cosméticas (sin validación especial)
    COSMETIC_SETTINGS = ['name', 'logo', 'business_hours', 'contact', 'late_arrival_grace_minutes']
    
    @classmethod
    def validate_change(cls, setting_name, new_value, old_value=None, tenant=None):
        """Valida un cambio de configuración"""
        result = {
            'valid': True,
            'setting_type': cls._get_setting_type(setting_name),
            'requires_confirmation': False,
            'impact_message': None,
            'validation_error': None
        }
        
        # Validar configuraciones críticas
        if setting_name in cls.CRITICAL_SETTINGS:
            config = cls.CRITICAL_SETTINGS[setting_name]
            result['requires_confirmation'] = config['requires_confirmation']
            result['impact_message'] = config['impact']
            
            # Validar valor
            try:
                if not config['validation'](new_value):
                    result['valid'] = False
                    result['validation_error'] = f"Valor inválido para {setting_name}"
            except (ValueError, TypeError):
                result['valid'] = False
                result['validation_error'] = f"Formato inválido para {setting_name}"
            
            # Validaciones especiales
            if setting_name == 'currency' and old_value and old_value != new_value:
                if cls._has_existing_transactions(tenant):
                    result['valid'] = False
                    result['validation_error'] = "No se puede cambiar la moneda con transacciones existentes"
        
        # Validar configuraciones sensibles
        elif setting_name in cls.SENSITIVE_SETTINGS:
            config = cls.SENSITIVE_SETTINGS[setting_name]
            result['impact_message'] = config['impact']
            
            try:
                if not config['validation'](new_value):
                    result['valid'] = False
                    result['validation_error'] = f"Valor inválido para {setting_name}"
            except (ValueError, TypeError):
                result['valid'] = False
                result['validation_error'] = f"Formato inválido para {setting_name}"
        
        return result
    
    @classmethod
    def _get_setting_type(cls, setting_name):
        """Determina el tipo de configuración"""
        if setting_name in cls.CRITICAL_SETTINGS:
            return 'critical'
        elif setting_name in cls.SENSITIVE_SETTINGS:
            return 'sensitive'
        else:
            return 'cosmetic'
    
    @classmethod
    def _has_existing_transactions(cls, tenant):
        """Verifica si existen transacciones que impidan cambiar la moneda"""
        if not tenant:
            return False
        
        try:
            from apps.pos_api.models import Sale
            return Sale.objects.filter(user__tenant=tenant, status='completed').exists()
        except:
            return False
    
    @classmethod
    def log_change(cls, tenant, user, setting_name, old_value, new_value, confirmed=False, impact_acknowledged=False):
        """Registra un cambio de configuración"""
        from .change_log_models import SettingsChangeLog
        
        setting_type = cls._get_setting_type(setting_name)
        
        SettingsChangeLog.objects.create(
            tenant=tenant,
            user=user,
            setting_name=setting_name,
            setting_type=setting_type,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value),
            confirmed=confirmed,
            impact_acknowledged=impact_acknowledged
        )
    
    @classmethod
    def get_critical_settings_info(cls):
        """Retorna información sobre configuraciones críticas para el frontend"""
        return {
            'critical': {name: {'impact': config['impact'], 'requires_confirmation': config['requires_confirmation']} 
                        for name, config in cls.CRITICAL_SETTINGS.items()},
            'sensitive': {name: {'impact': config['impact'], 'requires_confirmation': config['requires_confirmation']} 
                         for name, config in cls.SENSITIVE_SETTINGS.items()},
            'cosmetic': cls.COSMETIC_SETTINGS
        }