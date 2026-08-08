"""Exception handler DRF que produce el contrato de error estándar.

Shape de salida (ver `apps/core/exceptions.py`):

    {
        "code": "INSUFFICIENT_INVENTORY",
        "type": "BUSINESS",
        "message": "...",
        "details": {...},
        "incident_id": "ERR-20260806-AB29FD",   # solo FATAL / 5xx
        "timestamp": "2026-08-06T14:30:00Z",
        "trace_id": "9f1c2b3d-...",
        "severity": "WARNING",
        "origin": "Business",
    }

Reglas de retro-compatibilidad:
- Si el error es `ApiErrorException`, se usa su `code/type/message/details/origin`.
- Si el body del error (p.ej. `ValidationError` de DRF) ya trae `code`/`message`,
  se reutilizan y el resto del body va bajo `details`.
- Si no hay `code`/`type`, se infieren por `status_code`.
- `incident_id` solo en FATAL/5xx. `trace_id` siempre (reusa `request.request_id`).
- Nunca se expone stack trace.
"""
import logging
import secrets
from datetime import datetime, timezone

from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework.views import exception_handler as drf_exception_handler

from apps.core.exceptions import ApiErrorException

logger = logging.getLogger('api.errors')

# Mapeo status → (type, severity, origin, code por defecto)
_STATUS_MAP = {
    400: ('VALIDATION', 'WARNING', 'Validation', 'VALIDATION_ERROR'),
    401: ('AUTHENTICATION', 'WARNING', 'Auth', 'AUTHENTICATION_REQUIRED'),
    402: ('BUSINESS', 'WARNING', 'Subscription', 'PAYMENT_REQUIRED'),
    403: ('PERMISSION', 'WARNING', 'Auth', 'PERMISSION_DENIED'),
    404: ('NOT_FOUND', 'WARNING', 'Unknown', 'NOT_FOUND'),
    405: ('BUSINESS', 'WARNING', 'Unknown', 'METHOD_NOT_ALLOWED'),
    408: ('TIMEOUT', 'WARNING', 'Network', 'REQUEST_TIMEOUT'),
    429: ('RATE_LIMIT', 'WARNING', 'Unknown', 'RATE_LIMIT_EXCEEDED'),
    500: ('FATAL', 'CRITICAL', 'Unknown', 'INTERNAL_ERROR'),
    502: ('FATAL', 'CRITICAL', 'Network', 'BAD_GATEWAY'),
    503: ('FATAL', 'CRITICAL', 'Unknown', 'SERVICE_UNAVAILABLE'),
    504: ('FATAL', 'CRITICAL', 'Network', 'GATEWAY_TIMEOUT'),
}

SEVERITY_BY_TYPE = {
    'VALIDATION': 'WARNING',
    'BUSINESS': 'WARNING',
    'PERMISSION': 'WARNING',
    'AUTHENTICATION': 'WARNING',
    'NOT_FOUND': 'WARNING',
    'NETWORK': 'WARNING',
    'TIMEOUT': 'WARNING',
    'RATE_LIMIT': 'WARNING',
    'RECOVERABLE': 'ERROR',
    'FATAL': 'CRITICAL',
}


def _utcnow_iso():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _generate_incident_id():
    return f'ERR-{datetime.now(timezone.utc).strftime("%Y%m%d")}-{secrets.token_hex(3).upper()}'


def _trace_id_from_request(request):
    return getattr(request, 'request_id', None) or getattr(request, 'trace_id', None)


def _is_fatal(status_code, error_type):
    return status_code >= 500 or error_type == 'FATAL'


def exception_handler(exc, context):
    request = context.get('request')
    response = drf_exception_handler(exc, context)

    # Http404 no manejado por DRF → envolver
    if response is None and isinstance(exc, Http404):
        response = drf_exception_handler(drf_exceptions.NotFound(), context)

    if response is None:
        # Excepción no reconocida (500 real) → contrato FATAL y loggear
        response = drf_exception_handler(drf_exceptions.APIException(
            'Ocurrió un error inesperado.'
        ), context)
        if response is None:
            response = drf_exceptions.APIException('Ocurrió un error inesperado.').get_full_details()
            from rest_framework.response import Response
            from rest_framework import status as http_status
            response = Response({'detail': 'Ocurrió un error inesperado.'}, status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)

    status_code = response.status_code

    # 1. Prioridad: ApiErrorException tipada
    if isinstance(exc, ApiErrorException):
        contract = exc.as_contract()
        error_type = contract['type']
        origin = contract['origin']
        details = contract['details'] or {}
        code = contract['code']
        message = contract['message']
    else:
        data = response.data
        # 2. Body con code/message propios (retro-compatible) → reusar
        if isinstance(data, dict) and 'code' in data:
            code = data['code']
            message = data.get('message') or data.get('error') or _status_detail(data, status_code)
            error_type = data.get('type') or _STATUS_MAP.get(status_code, ('FATAL', 'CRITICAL', 'Unknown', 'INTERNAL_ERROR'))[0]
            origin = data.get('origin') or _STATUS_MAP.get(status_code, ('FATAL', 'CRITICAL', 'Unknown', 'INTERNAL_ERROR'))[2]
            details = {k: v for k, v in data.items() if k not in ('code', 'type', 'message', 'error')}
        else:
            # 3. DRF estándar: inference por status
            error_type, _, origin, code = _STATUS_MAP.get(status_code, ('FATAL', 'CRITICAL', 'Unknown', 'INTERNAL_ERROR'))
            message = _status_detail(data, status_code)
            details = data if isinstance(data, dict) else {'detail': data}

    severity = SEVERITY_BY_TYPE.get(error_type, 'ERROR')
    is_fatal = _is_fatal(status_code, error_type)

    trace_id = _trace_id_from_request(request)
    incident_id = None

    if is_fatal:
        incident_id = _generate_incident_id()
        _log_fatal(exc, request, incident_id, trace_id, status_code)
        try:
            import sentry_sdk
            sentry_sdk.set_tag('incident_id', incident_id)
            if trace_id:
                sentry_sdk.set_tag('trace_id', trace_id)
            sentry_sdk.capture_exception(exc)
        except Exception:
            logger.warning('Sentry tag/capture failed for incident %s', incident_id)

    payload = {
        'code': code,
        'type': error_type,
        'message': message,
        'details': details,
        'timestamp': _utcnow_iso(),
        'trace_id': trace_id,
        'severity': severity,
        'origin': origin,
    }
    if incident_id:
        payload['incident_id'] = incident_id

    response.data = payload
    return response


def _status_detail(data, status_code):
    """Extrae un mensaje plano del body DRF (puede ser lista/dict de errores)."""
    if isinstance(data, dict):
        detail = data.get('detail') or data.get('message') or data.get('error')
        if detail:
            return str(detail) if not isinstance(detail, (list, dict)) else str(detail)
        # Validación por campos → mensaje genérico, los detalles van en `details`
        if status_code == 400:
            return 'Revisa los campos marcados e inténtalo de nuevo.'
    if isinstance(data, list) and data:
        return str(data[0])
    return str(data) if data else 'Ocurrió un error inesperado.'


def _log_fatal(exc, request, incident_id, trace_id, status_code):
    logger.error(
        'FATAL %s status=%s path=%s incident=%s trace=%s exc=%s',
        type(exc).__name__, status_code,
        getattr(request, 'path', 'unknown'),
        incident_id, trace_id, str(exc),
        exc_info=(exc is not None),
    )
