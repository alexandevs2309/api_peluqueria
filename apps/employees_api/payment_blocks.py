"""
Enum de razones de bloqueo para pagos
SOLO EXPOSICIÓN - NO MODIFICA LÓGICA EXISTENTE
"""

class PaymentBlockReason:
    """Razones estándar por las que un pago puede estar bloqueado"""
    
    # Permisos y suscripción
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    SUBSCRIPTION_EXPIRED = "SUBSCRIPTION_EXPIRED" 
    TENANT_SUSPENDED = "TENANT_SUSPENDED"
    
    # Estado del sistema
    CASH_REGISTER_CLOSED = "CASH_REGISTER_CLOSED"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    NO_PENDING_SALES = "NO_PENDING_SALES"
    
    # Configuración de empleado
    EMPLOYEE_NOT_CONFIGURED = "EMPLOYEE_NOT_CONFIGURED"
    INVALID_PAYMENT_MODE = "INVALID_PAYMENT_MODE"
    NO_EARNINGS_AVAILABLE = "NO_EARNINGS_AVAILABLE"
    
    # Mensajes legibles para humanos
    MESSAGES = {
        INSUFFICIENT_PERMISSIONS: "No tienes permisos para procesar pagos. Se requiere rol de administrador.",
        SUBSCRIPTION_EXPIRED: "La suscripción del negocio está vencida. Contacta al administrador.",
        TENANT_SUSPENDED: "La cuenta está suspendida. Contacta al soporte técnico.",
        CASH_REGISTER_CLOSED: "La caja registradora debe estar abierta para procesar pagos en efectivo.",
        INSUFFICIENT_BALANCE: "El empleado no tiene balance suficiente para el pago solicitado.",
        NO_PENDING_SALES: "No hay ventas pendientes de pago para este empleado.",
        EMPLOYEE_NOT_CONFIGURED: "El empleado no está configurado para el modo de pago solicitado.",
        INVALID_PAYMENT_MODE: "El modo de pago del empleado no es válido para esta operación.",
        NO_EARNINGS_AVAILABLE: "No hay ganancias disponibles para pagar en este período."
    }
    
    @classmethod
    def get_message(cls, reason):
        """Obtiene mensaje legible para una razón de bloqueo"""
        return cls.MESSAGES.get(reason, "Pago bloqueado por razones de seguridad.")