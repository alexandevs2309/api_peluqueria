from django.contrib import admin
from .models import Role, UserRole, AdminActionLog

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')  # Campos visibles en la tabla
    search_fields = ('name',)
    filter_horizontal = ('permissions', 'users')  # Para mejor UI en M2M
    ordering = ('name',)

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'assigned_at')
    search_fields = ('user__email', 'role__name')
    list_filter = ('role',)
    ordering = ('-assigned_at',)

@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'timestamp')
    search_fields = ('user__email', 'action', 'ip_address')
    list_filter = ('timestamp',)
    ordering = ('-timestamp',)
