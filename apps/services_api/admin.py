from django.contrib import admin

from .models import Service, ServiceCategory


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'is_active', 'created_at')
    list_filter = ('is_active', 'tenant')
    search_fields = ('name',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'price', 'duration', 'is_active')
    list_filter = ('is_active', 'tenant')
    search_fields = ('name', 'description')
