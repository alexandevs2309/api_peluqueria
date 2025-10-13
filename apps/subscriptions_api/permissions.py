from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework import status
from functools import wraps

class HasFeaturePermission(BasePermission):
    """
    Permission class to check if user's tenant has specific feature
    """
    def __init__(self, feature_name):
        self.feature_name = feature_name

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
            
        if not request.user.tenant:
            return False
            
        tenant = request.user.tenant
        if not tenant.subscription_plan:
            return False
            
        features = tenant.subscription_plan.features or {}
        return features.get(self.feature_name, False)

def requires_feature(feature_name):
    """
    Decorator to check if user has access to specific feature
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return Response(
                    {"error": "Authentication required"}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
                
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
                
            features = tenant.subscription_plan.features or {}
            if not features.get(feature_name, False):
                return Response(
                    {"error": f"Feature '{feature_name}' not available in your plan"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
                
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def check_user_limit(tenant):
    """
    Check if tenant can add more users
    """
    if tenant.max_users == 0:  # Unlimited
        return True
    current_users = tenant.users.filter(is_active=True).count()
    return current_users < tenant.max_users

def check_employee_limit(tenant):
    """
    Check if tenant can add more employees
    """
    if tenant.max_employees == 0:  # Unlimited
        return True
    # Assuming employees are users with ClientStaff role
    current_employees = tenant.users.filter(
        is_active=True, 
        role='ClientStaff'
    ).count()
    return current_employees < tenant.max_employees

class IsSuperuserOrReadOnly(BasePermission):
    """
    Permission that allows superusers full access, others read-only
    """
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.is_superuser