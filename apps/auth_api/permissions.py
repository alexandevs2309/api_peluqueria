# apps/auth_api/permissions.py
from rest_framework.permissions import BasePermission
from apps.roles_api.permissions import RolePermission

class IsAdmin(RolePermission):
    allowed_roles = ['Admin']

class IsStylist(RolePermission):
    allowed_roles = ['Stylist']

class IsClient(RolePermission):
    allowed_roles = ['Client']

class IsUtility(RolePermission):
    allowed_roles = ['Utility']