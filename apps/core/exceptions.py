"""Excepciones tipadas de API (contrato de error estándar).

Toda respuesta de error HTTP debe producir el contrato:

    code, type, message, details, incident_id, timestamp, trace_id, severity, origin

Estas excepciones se elevan en las vistas/middlewares y son convertidas por
`apps.core.exceptions_handler.exception_handler` en el shape estándar.
"""
from rest_framework.exceptions import APIException


class ApiErrorException(APIException):
    """Base de errores de API con el contrato estándar."""

    code = 'GENERIC'
    error_type = 'FATAL'
    origin = 'Unknown'
    incident_id = None
    default_detail = 'Ocurrió un error inesperado.'
    default_code = 'GENERIC'

    def __init__(self, detail=None, code=None, status_code=None, details=None,
                 origin=None, error_type=None):
        super().__init__(detail or self.default_detail, code or self.default_code)
        if status_code is not None:
            self.status_code = status_code
        self.details = details or {}
        self.origin = origin or self.origin
        if error_type is not None:
            self.error_type = error_type

    def as_contract(self):
        """Devuelve el payload estándar (sin incident_id: lo asigna el handler)."""
        return {
            'code': self.code,
            'type': self.error_type,
            'message': str(self.detail),
            'details': self.details,
            'origin': self.origin,
        }


class ValidationError(ApiErrorException):
    status_code = 400
    error_type = 'VALIDATION'
    origin = 'Validation'
    default_detail = 'Datos inválidos.'
    default_code = 'VALIDATION_ERROR'


class BusinessError(ApiErrorException):
    status_code = 422
    error_type = 'BUSINESS'
    origin = 'Business'
    default_detail = 'La operación no pudo completarse.'
    default_code = 'BUSINESS_ERROR'


class PermissionError(ApiErrorException):
    status_code = 403
    error_type = 'PERMISSION'
    origin = 'Auth'
    default_detail = 'No tienes permisos para realizar esta acción.'
    default_code = 'PERMISSION_DENIED'


class AuthenticationError(ApiErrorException):
    status_code = 401
    error_type = 'AUTHENTICATION'
    origin = 'Auth'
    default_detail = 'Sesión inválida o expirada.'
    default_code = 'AUTHENTICATION_REQUIRED'


class NotFoundError(ApiErrorException):
    status_code = 404
    error_type = 'NOT_FOUND'
    origin = 'Unknown'
    default_detail = 'No se encontró el recurso solicitado.'
    default_code = 'NOT_FOUND'


class SubscriptionError(ApiErrorException):
    status_code = 402
    error_type = 'BUSINESS'
    origin = 'Subscription'
    default_detail = 'La suscripción requiere atención.'
    default_code = 'SUBSCRIPTION_REQUIRED'


class PaymentError(ApiErrorException):
    status_code = 402
    error_type = 'BUSINESS'
    origin = 'Payment'
    default_detail = 'El pago no pudo procesarse.'
    default_code = 'PAYMENT_ERROR'


class RateLimitError(ApiErrorException):
    status_code = 429
    error_type = 'RATE_LIMIT'
    origin = 'Unknown'
    default_detail = 'Demasiadas solicitudes. Intenta de nuevo más tarde.'
    default_code = 'RATE_LIMIT_EXCEEDED'


class ServiceUnavailableError(ApiErrorException):
    status_code = 503
    error_type = 'FATAL'
    origin = 'Unknown'
    default_detail = 'El servicio no está disponible en este momento.'
    default_code = 'SERVICE_UNAVAILABLE'
