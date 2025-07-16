from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin 
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

    search_fields = ('email', 'full_name')
    ordering = ('email',)

  
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('full_name', 'phone', 'is_email_verified', 'mfa_enabled', 'mfa_secret')}), 
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

   
    @admin.display(description='Roles Asignados')
    def get_roles_display(self, obj):
        roles = UserRole.objects.filter(user=obj).select_related('role')
        return ", ".join([user_role.role.name for user_role in roles])




admin.site.register(AccessLog)
admin.site.register(ActiveSession)
admin.site.register(LoginAudit)