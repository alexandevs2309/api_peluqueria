"""Middleware de utilidades cross-cutting para logging y performance.

Contiene:
- StructuredLoggingMiddleware: Logging JSON estructurado con request_id
- SlowQueryMiddleware: Detección de queries lentas >200ms
"""
import logging
import json
import time
import uuid
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


class SlowQueryMiddleware(MiddlewareMixin):
    """Detectar y alertar queries lentas >200ms"""
    
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
