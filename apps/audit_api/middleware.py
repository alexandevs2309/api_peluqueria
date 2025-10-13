import json
from django.utils.deprecation import MiddlewareMixin
from django.contrib.contenttypes.models import ContentType
from .utils import create_audit_log

class AuditLogMiddleware(MiddlewareMixin):
    """Middleware to log user actions"""
    
    def process_request(self, request):
        # Store original state for update operations
        if request.method in ['PUT', 'PATCH']:
            request._audit_original_state = {}
        return None
    
    def process_response(self, request, response):
        # Log authentication actions
        if request.path.startswith('/api/auth/'):
            if request.method == 'POST':
                if 'login' in request.path.lower():
                    action = 'LOGIN' if response.status_code == 200 else 'LOGIN_FAILED'
                    from .utils import get_client_ip
                    client_ip = get_client_ip(request)
                    
                    if request.user.is_authenticated:
                        create_audit_log(
                            user=request.user,
                            action=action,
                            description=f"Login attempt from {client_ip}",
                            request=request,
                            source='AUTH'
                        )
                    else:
                        create_audit_log(
                            user=None,
                            action=action,
                            description=f"Login attempt from {client_ip}",
                            request=request,
                            source='AUTH'
                        )
        return response
