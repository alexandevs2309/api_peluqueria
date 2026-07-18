import json
from django.utils.deprecation import MiddlewareMixin
from django.contrib.contenttypes.models import ContentType
from .utils import create_audit_log

class AuditLogMiddleware(MiddlewareMixin):
    """Middleware to log user actions (non-auth actions only — auth logging is handled by views)"""
    
    def process_request(self, request):
        # Store original state for update operations
        if request.method in ['PUT', 'PATCH']:
            request._audit_original_state = {}
        return None
    
    def process_response(self, request, response):
        # Skip auth paths — CookieLoginView already creates LoginAudit + AccessLog
        if request.path.startswith('/api/auth/'):
            return response
        
        # Log other write actions
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and response.status_code < 400:
            if not request.path.startswith('/api/'):
                return response
            create_audit_log(
                user=request.user if request.user.is_authenticated else None,
                action=f'{request.method} {request.path}',
                description=f'{request.method} {request.path} — {response.status_code}',
                request=request,
                source='API'
            )
        return response
