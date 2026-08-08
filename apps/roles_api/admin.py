# apps/roles_api/admin.py
from django.contrib import admin
from .models import Role, UserRole, AdminActionLog


class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 1
    fields = ('user', 'assigned_at') # Aquí muestras el campo 'user'
    readonly_fields = ('assigned_at',)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
    filter_horizontal = ('permissions',) # Ya habías corregido la coma aquí
    inlines = [UserRoleInline]

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'timestamp')
    list_filter = ('timestamp', 'user')
    search_fields = ('user__email', 'action', 'ip_address')
    readonly_fields = ('user', 'action', 'ip_address', 'user_agent', 'timestamp')

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions
