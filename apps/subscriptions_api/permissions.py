from rest_framework.permissions import BasePermission
from .utils import get_user_feature_flag

class IsSuperuserOrReadOnly(BasePermission):

    def has_permission(self, request, view):
        # Allow read-only access for all users
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        # Allow full access for superusers or users with Super-Admin role
        if request.user and request.user.is_superuser:
            return True
        # Check if user has Super-Admin role
        if request.user and hasattr(request.user, 'roles'):
            user_roles = [role.name for role in request.user.roles.all()]
            return 'Super-Admin' in user_roles
        return False
    

class HasFeatureEnabled(BasePermission):



    feature_name = None

    def has_permission(self, request, view):
        if not request.user or  not request.user.is_authenticated:
            return False
        return get_user_feature_flag(request.user , self.feature_name)
    

# Ejemplos específicos
class CanAccessReports(HasFeatureEnabled):
    feature_name = "reports_enabled"

class CanExportData(HasFeatureEnabled):
    feature_name = "export_enabled"