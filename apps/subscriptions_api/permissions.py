from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework import status
from functools import wraps
from .plan_consistency import can_add_employee, can_add_user, tenant_has_feature

class HasFeaturePermission(BasePermission):
    """
    Permission class to check if user's tenant has specific feature
    """
    def __init__(self, feature_name=None):
        self.feature_name = feature_name

    def has_permission(self, request, view):
        feature_name = self.feature_name or getattr(view, 'required_feature', None)

        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
            
        if not request.user.tenant:
            return False
            
        tenant = request.user.tenant
        if not tenant.subscription_plan:
            return False
            
        if not feature_name:
            return False
        return tenant_has_feature(tenant, feature_name, default=False)

def requires_feature(feature_name):
    """
    Decorator to check if user has access to specific feature
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self_or_request, *args, **kwargs):
            # Compatible con ViewSet methods (self, request) y funciones (request)
            from rest_framework.viewsets import ViewSetMixin
            if isinstance(self_or_request, ViewSetMixin):
                self = self_or_request
                request = args[0]
                args = args[1:]
                call = lambda: view_func(self, request, *args, **kwargs)
            else:
                request = self_or_request
                call = lambda: view_func(request, *args, **kwargs)
            if not request.user.is_authenticated:
                return Response(
                    {"error": "Authentication required"}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            if request.user.is_superuser:
                return call()
                
            if not request.user.tenant:
                return Response(
                    {"error": "No tenant assigned"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
                
            tenant = request.user.tenant
            if not tenant.subscription_plan:
                return Response(
                    {"error": "No subscription plan"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
                
            if not tenant_has_feature(tenant, feature_name, default=False):
                return Response(
                    {"error": f"Feature '{feature_name}' not available in your plan"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
                
            return call()
        return wrapper
    return decorator

def check_user_limit(tenant):
    """
    Check if tenant can add more users
    """
    return can_add_user(tenant)

def check_employee_limit(tenant):
    """
    Check if tenant can add more employees
    """
    return can_add_employee(tenant)

class IsSuperuserOrReadOnly(BasePermission):
    """
    Permission that allows superusers full access, others read-only
    """
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.is_superuser
