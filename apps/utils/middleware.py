"""
Middleware para correlación de requests y logging estructurado
"""
import uuid
import structlog
from django.utils.deprecation import MiddlewareMixin

logger = structlog.get_logger(__name__)

class RequestCorrelationMiddleware(MiddlewareMixin):
    """
    Agrega request_id único a cada request para correlación de logs
    """
    
    def process_request(self, request):
        # Generar request_id único
        request_id = str(uuid.uuid4())[:8]
        request.request_id = request_id
        
        # Configurar contexto structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            user_id=getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None,
            tenant_id=getattr(request, 'tenant_id', None),
            path=request.path,
            method=request.method,
            ip=self._get_client_ip(request)
        )
        
        # Log inicio de request
        logger.info("request_started",
                   path=request.path,
                   method=request.method,
                   user_agent=request.META.get('HTTP_USER_AGENT', '')[:100])
    
    def process_response(self, request, response):
        # Log fin de request
        logger.info("request_completed",
                   status_code=response.status_code,
                   content_length=len(response.content) if hasattr(response, 'content') else 0)
        
        # Limpiar contexto
        structlog.contextvars.clear_contextvars()
        
        return response
    
    def process_exception(self, request, exception):
        # Log excepción
        logger.error("request_exception",
                    exception_type=type(exception).__name__,
                    exception_message=str(exception),
                    exc_info=True)
        
        return None
    
    def _get_client_ip(self, request):
        """Obtiene IP real del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip