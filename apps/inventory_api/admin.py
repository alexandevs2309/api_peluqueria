from django.contrib import admin
from apps.tenants_api.base_admin import BaseTenantAdmin
from .models import Product, Supplier, StockMovement

@admin.register(Product)
class ProductAdmin(BaseTenantAdmin):
    list_display = ['name', 'sku', 'price', 'stock', 'category', 'is_active', 'tenant']
    list_filter = ['category', 'is_active', 'tenant']
    search_fields = ['name', 'sku']
    list_editable = ['price', 'stock', 'is_active']

@admin.register(Supplier)
class SupplierAdmin(BaseTenantAdmin):
    list_display = ['name', 'phone', 'email', 'tenant']
    search_fields = ['name']

@admin.register(StockMovement)
class StockMovementAdmin(BaseTenantAdmin):
    tenant_lookup = "product__tenant"
    list_display = ['product', 'quantity', 'reason', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['created_at']
