"""Middleware de utilidades cross-cutting para logging y performance.

Contiene:
- StructuredLoggingMiddleware: Logging JSON estructurado con request_id
- SlowQueryMiddleware: Detección de queries lentas >200ms
- MaintenanceMiddleware: Modo mantenimiento vía env var
"""
import logging
import json
import time
import uuid
import os
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('api.requests')


class StructuredLoggingMiddleware(MiddlewareMixin):
    """Logging estructurado JSON con contexto completo"""
    
    def process_request(self, request):
        request.request_id = str(uuid.uuid4())
        request.start_time = time.time()
        return None
    
    def process_response(self, request, response):
        if not hasattr(request, 'start_time'):
            return response
        
        duration_ms = (time.time() - request.start_time) * 1000
        
        log_data = {
            'request_id': getattr(request, 'request_id', 'unknown'),
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration_ms': round(duration_ms, 2),
            'user_id': request.user.id if request.user.is_authenticated else None,
            'tenant_id': request.tenant.id if hasattr(request, 'tenant') and request.tenant else None,
            'ip': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
        }
        
        # Log según status code
        if response.status_code >= 500:
            logger.error(json.dumps(log_data))
        elif response.status_code >= 400:
            logger.warning(json.dumps(log_data))
        else:
            logger.info(json.dumps(log_data))
        
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


"""Middleware de utilidades cross-cutting para logging y performance.

Contiene:
- StructuredLoggingMiddleware: Logging JSON estructurado con request_id
- ErrorContextMiddleware: Headers X-Trace-Id / X-Incident-Id + incident_id en 5xx
- SlowQueryMiddleware: Detección de queries lentas >200ms
- MaintenanceMiddleware: Modo mantenimiento vía env var
"""
import logging
import json
import secrets
import time
import uuid
import os
from datetime import datetime, timezone
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('api.requests')


def _generate_incident_id():
    return f'ERR-{datetime.now(timezone.utc).strftime("%Y%m%d")}-{secrets.token_hex(3).upper()}'


class ErrorContextMiddleware(MiddlewareMixin):
    """Correlación de errores: inyecta X-Trace-Id y genera incident_id en 5xx.

    - Reusa `request.request_id` (StructuredLoggingMiddleware) como trace_id.
    - En 5xx que escapen del exception_handler de DRF (p.ej. vistas Django puras)
      genera un `incident_id`, lo loggea y lo expone en `X-Incident-Id`.
    - Normaliza respuestas de error ad-hoc de middlewares (`JsonResponse` con
      `error`/`code`) agregando los campos del contrato estándar, sin romper
      los campos existentes (retro-compatibilidad).
    """

    def process_request(self, request):
        if not hasattr(request, 'request_id'):
            request.request_id = str(uuid.uuid4())
        return None

    def process_response(self, request, response):
        trace_id = getattr(request, 'request_id', None) or getattr(request, 'trace_id', None)
        if trace_id:
            response['X-Trace-Id'] = trace_id

        body = self._json_body(response)

        # Incident id solo en 5xx
        if response.status_code >= 500:
            existing = body.get('incident_id') if isinstance(body, dict) else None
            if not existing:
                incident_id = _generate_incident_id()
                response['X-Incident-Id'] = incident_id
                logger.error(
                    'UNHANDLED 5xx path=%s status=%s incident=%s trace=%s',
                    getattr(request, 'path', 'unknown'),
                    response.status_code,
                    incident_id,
                    trace_id,
                )
                try:
                    import sentry_sdk
                    sentry_sdk.set_tag('incident_id', incident_id)
                    if trace_id:
                        sentry_sdk.set_tag('trace_id', trace_id)
                except Exception:
                    pass

        # Normalizar respuestas de error ad-hoc de middlewares (retro-compatible)
        if response.status_code >= 400 and isinstance(response, JsonResponse) and isinstance(body, dict):
            if 'code' in body and 'type' not in body:
                status_code = response.status_code
                from apps.core.exceptions_handler import _STATUS_MAP, SEVERITY_BY_TYPE
                error_type, severity, origin, _ = _STATUS_MAP.get(
                    status_code, ('FATAL', 'CRITICAL', 'Unknown', 'INTERNAL_ERROR'))
                body['type'] = body.get('type', error_type)
                body['severity'] = SEVERITY_BY_TYPE.get(body['type'], 'ERROR')
                body['origin'] = origin
                body['timestamp'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                body['trace_id'] = trace_id
                from django.core.serializers.json import DjangoJSONEncoder
                response.content = json.dumps(body, cls=DjangoJSONEncoder)
                response['Content-Type'] = 'application/json'

        return response

    @staticmethod
    def _json_body(response):
        """Devuelve el body parseado si es JSON, si no None."""
        if not isinstance(response, JsonResponse):
            return None
        try:
            return json.loads(response.content)
        except (ValueError, TypeError):
            return None


class SlowQueryMiddleware(MiddlewareMixin):
    
    def process_response(self, request, response):
        from django.db import connection
        from django.conf import settings
        
        if not settings.DEBUG and hasattr(connection, 'queries'):
            slow_queries = [
                q for q in connection.queries 
                if float(q.get('time', 0)) > 0.2  # >200ms
            ]
            
            if slow_queries:
                try:
                    import sentry_sdk
                    sentry_sdk.capture_message(
                        f'Slow queries detected: {len(slow_queries)} queries >200ms',
                        level='warning',
                        extras={
                            'path': request.path,
                            'method': request.method,
                            'slow_queries': slow_queries[:5],  # Primeras 5
                            'total_queries': len(connection.queries),
                        }
                    )
                except ImportError:
                    logger = logging.getLogger('performance')
                    logger.warning(f'Slow queries on {request.path}: {len(slow_queries)} queries >200ms')
        
        return response
