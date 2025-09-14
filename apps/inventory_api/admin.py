from django.contrib import admin
from .models import Product, Supplier, StockMovement

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'price', 'stock', 'category', 'is_active', 'tenant']
    list_filter = ['category', 'is_active', 'tenant']
    search_fields = ['name', 'sku']
    list_editable = ['price', 'stock', 'is_active']

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'tenant']
    search_fields = ['name']

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity', 'reason', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['created_at']
