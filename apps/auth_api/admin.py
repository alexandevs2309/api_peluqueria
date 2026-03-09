from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.tenants_api.base_admin import BaseTenantAdmin
from .models import User, AccessLog, ActiveSession, LoginAudit
from apps.roles_api.models import UserRole


class UserRoleInlineForUser(admin.TabularInline):
    model = UserRole
    extra = 1
    fields = ('role', 'assigned_at',) 
    readonly_fields = ('assigned_at',)

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'is_active', 'is_staff', 'get_roles_display')
    list_filter = ('is_active', 'is_staff', 'is_email_verified')

    readonly_fields = ('mfa_secret',)

    def get_queryset(self, request):
        qs = super().get_queryset(request).filter(is_deleted=False)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'tenant') and request.user.tenant:
            return qs.filter(tenant=request.user.tenant)
        return qs.none()

    search_fields = ('email', 'full_name')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('full_name', 'phone', 'is_email_verified', 'mfa_enabled')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Security Logs', {'fields': ('last_login_ip_address',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'phone', 'password', 'password2'),
        }),
    )

    inlines = (UserRoleInlineForUser,) + BaseUserAdmin.inlines

    def has_module_permission(self, request):
        if not super().has_module_permission(request):
            return False
        if request.user.is_superuser:
            return True
        return hasattr(request.user, 'tenant') and request.user.tenant is not None

    def has_view_permission(self, request, obj=None):
        if not super().has_view_permission(request, obj):
            return False
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, 'tenant') or request.user.tenant is None:
            return False
        if obj is None:
            return True
        return obj.tenant == request.user.tenant

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, 'tenant') or request.user.tenant is None:
            return False
        if obj is None:
            return True
        return obj.tenant == request.user.tenant

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj):
            return False
        if request.user.is_superuser:
            return True
        if not hasattr(request.user, 'tenant') or request.user.tenant is None:
            return False
        if obj is None:
            return True
        return obj.tenant == request.user.tenant

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.tenant = request.user.tenant
            obj.is_superuser = False
        super().save_model(request, obj, form, change)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    @admin.display(description='Roles Asignados')
    def get_roles_display(self, obj):
        roles = UserRole.objects.filter(user=obj).select_related('role')
        return ", ".join([user_role.role.name for user_role in roles])


@admin.register(AccessLog)
class AccessLogAdmin(BaseTenantAdmin):
    tenant_lookup = "user__tenant"
    list_display = ('user', 'event_type', 'ip_address', 'timestamp')
    list_filter = ('event_type', 'timestamp')
    readonly_fields = ('user', 'event_type', 'ip_address', 'user_agent', 'timestamp')

    def has_add_permission(self, request):
        return False


@admin.register(ActiveSession)
class ActiveSessionAdmin(BaseTenantAdmin):
    tenant_lookup = "tenant"
    list_display = ('user', 'tenant', 'ip_address', 'created_at', 'last_seen', 'is_active')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('user', 'tenant', 'ip_address', 'user_agent', 'token_jti', 'refresh_token', 'created_at', 'last_seen', 'is_active', 'expired_at')

    def has_add_permission(self, request):
        return False


@admin.register(LoginAudit)
class LoginAuditAdmin(BaseTenantAdmin):
    tenant_lookup = "user__tenant"
    list_display = ('user', 'ip_address', 'successful', 'message', 'timestamp')
    list_filter = ('successful', 'timestamp')
    readonly_fields = ('user', 'ip_address', 'user_agent', 'successful', 'message', 'timestamp')

    def has_add_permission(self, request):
        return False
