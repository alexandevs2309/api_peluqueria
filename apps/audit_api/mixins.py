"""
Audit Logging Mixin for Django REST Framework ViewSets
Provides automatic audit logging for CRUD operations
"""

from rest_framework import viewsets
from .utils import create_audit_log
from django.contrib.contenttypes.models import ContentType
from django.utils.deprecation import MiddlewareMixin


class AuditLoggingMixin:
    """
    Mixin that automatically logs CRUD operations for ModelViewSet
    """
    
    def get_action_type(self, action):
        """Map DRF action to audit log action type"""
        action_map = {
            'create': 'CREATE',
            'retrieve': 'VIEW',
            'update': 'UPDATE',
            'partial_update': 'UPDATE',
            'destroy': 'DELETE',
            'list': 'VIEW',
        }
        return action_map.get(action, 'VIEW')
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def log_action(self, action, instance, user, request=None):
        """Create audit log entry"""
        description = f"{action} {instance.__class__.__name__}: {str(instance)}"
        
        create_audit_log(
            user=user,
            action=self.get_action_type(action),
            description=description,
            content_object=instance,
            ip_address=self.get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else None,
            source=self.get_source_from_model(instance),
            extra_data={
                'view_action': action,
                'model_name': instance.__class__.__name__,
                'model_verbose_name': instance._meta.verbose_name,
            }
        )
    
    def get_source_from_model(self, instance):
        """Determine source based on model's app label"""
        app_label = instance._meta.app_label
        source_map = {
            'clients_api': 'USERS',
            'appointments_api': 'APPOINTMENTS',
            'services_api': 'SERVICES',
            'inventory_api': 'INVENTORY',
            'pos_api': 'POS',
            'billing_api': 'BILLING',
            'subscriptions_api': 'SUBSCRIPTIONS',
            'settings_api': 'SETTINGS',
            'roles_api': 'ROLES',
            'auth_api': 'AUTH',
        }
        return source_map.get(app_label, 'SYSTEM')
    
    def perform_create(self, serializer):
        """Override to add audit logging"""
        instance = serializer.save()
        self.log_action('create', instance, self.request.user, self.request)
        return instance
    
    def perform_update(self, serializer):
        """Override to add audit logging"""
        instance = serializer.save()
        self.log_action('update', instance, self.request.user, self.request)
        return instance
    
    def perform_destroy(self, instance):
        """Override to add audit logging"""
        self.log_action('destroy', instance, self.request.user, self.request)
        instance.delete()
    
    def retrieve(self, request, *args, **kwargs):
        """Override to add view logging"""
        response = super().retrieve(request, *args, **kwargs)
        instance = self.get_object()
        self.log_action('retrieve', instance, request.user, request)
        return response
    




class AuditLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT')
            action = f"{request.method} {request.path}"
            description = f"User {request.user.username} performed {action}"
            create_audit_log(
                user=request.user,
                action='VIEW',
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                source='SYSTEM'
            )
