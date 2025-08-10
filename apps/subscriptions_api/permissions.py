from rest_framework.permissions import BasePermission
from .utils import get_user_feature_flag

class IsSuperuserOrReadOnly(BasePermission):

    def has_permission(self, request, view):
        # Allow read-only access for all users
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        # Allow full access for superusers
        return request.user and request.user.is_superuser
    

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