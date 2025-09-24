from django.db import models
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

class Role(models.Model):
    ROLE_TYPES = [
        ('global', 'Global'),
        ('tenant', 'Tenant'),
    ]
    
    GLOBAL_ROLES = [
        ('super_admin', 'Super Admin'),
        ('support', 'Soporte'),
    ]
    
    TENANT_ROLES = [
        ('client_admin', 'Client Admin'),
        ('manager', 'Manager'),
        ('cashier', 'Cajera'),
        ('stylist', 'Estilista'),
        ('staff', 'Utility/Staff'),
    ]

    name = models.CharField(max_length=50)
    code = models.CharField(max_length=30, unique=True)
    role_type = models.CharField(max_length=10, choices=ROLE_TYPES)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_role_type_display()})"

class UserRole(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='assigned_roles')

    class Meta:
        unique_together = ['user', 'role', 'tenant']

    def __str__(self):
        tenant_info = f" en {self.tenant.name}" if self.tenant else " (Global)"
        return f"{self.user.username} - {self.role.name}{tenant_info}"

# Permisos específicos por módulo
PERMISSIONS_MAP = {
    # Roles Globales
    'super_admin': [
        'add_tenant', 'change_tenant', 'delete_tenant', 'view_tenant',
        'add_subscriptionplan', 'change_subscriptionplan', 'delete_subscriptionplan', 'view_subscriptionplan',
        'add_user', 'change_user', 'delete_user', 'view_user',
        'view_global_reports', 'manage_system_settings'
    ],
    'support': [
        'view_tenant', 'view_user', 'change_user_password', 'suspend_user_account'
    ],
    
    # Roles por Tenant
    'client_admin': [
        'manage_employees', 'manage_pos', 'view_reports', 'manage_local_settings', 
        'manage_subscription', 'manage_inventory', 'manage_schedule'
    ],
    'manager': [
        'manage_schedule', 'manage_inventory', 'manage_pos', 'view_reports'
    ],
    'cashier': [
        'use_pos', 'process_payments', 'generate_invoices'
    ],
    'stylist': [
        'view_own_schedule', 'manage_assigned_clients', 'update_service_status'
    ],
    'staff': [
        'mark_attendance', 'view_schedule', 'basic_operations'
    ]
}