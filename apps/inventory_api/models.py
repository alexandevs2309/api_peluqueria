from django.db import models


class ProductCategory(models.Model):
    name = models.CharField(max_length=100)
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE, related_name='product_categories')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Categoría de Producto'
        verbose_name_plural = 'Categorías de Productos'
        unique_together = ('name', 'tenant')
        ordering = ['name']
        indexes = [
            models.Index(fields=['tenant']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=255)
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE, related_name='suppliers')
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    tenant = models.ForeignKey('tenants_api.Tenant', on_delete=models.CASCADE, related_name='products')
    sku = models.CharField(max_length=100)
    barcode = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    min_stock = models.PositiveIntegerField(default=1)
    unit = models.CharField(max_length=50, default='unidad')
    is_active = models.BooleanField(default=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True, default='')
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    image = models.ImageField(upload_to='', blank=True, null=True)

    class Meta:
        permissions = [
            ('adjust_stock', 'Can adjust product stock'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['sku', 'tenant'], name='unique_sku_per_tenant'),
            models.UniqueConstraint(fields=['barcode', 'tenant'], name='unique_barcode_per_tenant', condition=models.Q(barcode__isnull=False))
        ]
        indexes = [
            models.Index(fields=['tenant', 'sku']),
            models.Index(fields=['tenant', 'is_active']),
        ]

    @property
    def is_below_min_stock(self):
        return self.stock <= self.min_stock

    def __str__(self):
        return self.name

class StockMovement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    quantity = models.IntegerField()  # negativo si es salida
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
