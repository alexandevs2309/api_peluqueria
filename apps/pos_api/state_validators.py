"""
Validadores de estado para POS
FASE 2: Consistencia de estados
"""
from django.core.exceptions import ValidationError

class SaleStateValidator:
    """Validador de estados y transiciones de ventas"""
    
    VALID_STATES = ['pending', 'completed', 'cancelled', 'refunded']
    
    VALID_TRANSITIONS = {
        'pending': ['completed', 'cancelled'],
        'completed': ['refunded'],
        'cancelled': [],  # Estado final
        'refunded': []    # Estado final
    }
    
    @classmethod
    def validate_state(cls, status):
        """Validar que el estado sea válido"""
        if status not in cls.VALID_STATES:
            raise ValidationError(f"Estado inválido: {status}")
    
    @classmethod
    def validate_transition(cls, from_status, to_status):
        """Validar que la transición sea permitida"""
        cls.validate_state(from_status)
        cls.validate_state(to_status)
        
        if from_status == to_status:
            return True  # Sin cambio
        
        allowed_transitions = cls.VALID_TRANSITIONS.get(from_status, [])
        if to_status not in allowed_transitions:
            raise ValidationError(
                f"Transición inválida: {from_status} → {to_status}. "
                f"Permitidas: {allowed_transitions}"
            )
    
    @classmethod
    def validate_consistency(cls, status, closed):
        """Validar consistencia entre status y closed"""
        # Reglas de consistencia
        if status in ['cancelled', 'refunded'] and not closed:
            raise ValidationError(
                f"Venta {status} debe estar cerrada (closed=True)"
            )
        
        if status == 'pending' and closed:
            raise ValidationError(
                "Venta pendiente no puede estar cerrada"
            )
    
    @classmethod
    def can_generate_earnings(cls, status):
        """Determinar si una venta puede generar earnings"""
        return status == 'completed'
    
    @classmethod
    def should_revert_earnings(cls, old_status, new_status):
        """Determinar si se deben revertir earnings"""
        return (old_status == 'completed' and 
                new_status in ['cancelled', 'refunded'])

class CashRegisterStateValidator:
    """Validador de estados de caja registradora"""
    
    @classmethod
    def validate_open_operation(cls, register):
        """Validar que se puede operar con la caja"""
        if not register.is_open:
            raise ValidationError("Caja registradora está cerrada")
        
        if register.closed_at is not None:
            raise ValidationError("Caja registradora ya fue cerrada")
    
    @classmethod
    def validate_close_operation(cls, register, final_cash):
        """Validar que se puede cerrar la caja"""
        from decimal import Decimal
        
        if not register.is_open:
            raise ValidationError("Caja registradora ya está cerrada")
        
        if register.closed_at is not None:
            raise ValidationError("Caja registradora ya fue cerrada anteriormente")
        
        # VALIDACIÓN CRÍTICA: Efectivo contado debe coincidir con esperado (tolerancia ±$0.05)
        expected_cash = Decimal(str(register.display_amount))
        final_cash_decimal = Decimal(str(final_cash))
        
        difference = final_cash_decimal - expected_cash
        tolerance = Decimal('0.05')  # Tolerancia de 5 centavos
        
        if abs(difference) > tolerance:
            raise ValidationError(
                f"Efectivo contado ${final_cash_decimal} no coincide con esperado ${expected_cash}. "
                f"Diferencia: ${difference}. Tolerancia máxima: ±${tolerance}"
            )