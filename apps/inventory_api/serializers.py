from rest_framework import serializers
from django.utils.text import slugify
from .models import Product, StockMovement, Supplier, ProductCategory


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'


class ProductCategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'description', 'is_active', 'product_count']
        read_only_fields = ['product_count']

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()


class ProductSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(required=False, allow_blank=True, max_length=100)
    category = serializers.PrimaryKeyRelatedField(
        queryset=ProductCategory.objects.all(), allow_null=True, required=False
    )
    category_name = serializers.SerializerMethodField()
    description = serializers.CharField(default='', allow_blank=True, required=False)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'barcode', 'price', 'stock', 'min_stock', 
                  'unit', 'is_active', 'description', 'category', 'category_name', 
                  'image', 'image_url']
        read_only_fields = ['id', 'category_name', 'image_url']

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def _get_tenant(self):
        request = self.context.get('request')
        if not request:
            return None
        return getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)

    def _generate_sku(self, attrs):
        tenant = self._get_tenant()
        base_name = attrs.get('name') or (self.instance.name if self.instance else '') or 'PRODUCT'
        base = slugify(base_name).upper().replace('-', '')[:8] or 'PRODUCT'
        prefix = f"PRD-{base}"

        for i in range(1, 10000):
            candidate = f"{prefix}-{i:03d}"
            exists = Product.objects.filter(sku=candidate, tenant=tenant)
            if self.instance:
                exists = exists.exclude(pk=self.instance.pk)
            if not exists.exists():
                return candidate

        return f"{prefix}-X001"

    def validate(self, attrs):
        sku = attrs.get('sku', None)

        if not self.instance and (sku is None or str(sku).strip() == ''):
            attrs['sku'] = self._generate_sku(attrs)
            return super().validate(attrs)

        if self.instance and sku is None:
            return super().validate(attrs)

        if str(sku).strip() == '':
            attrs['sku'] = self._generate_sku(attrs)
        else:
            attrs['sku'] = str(sku).strip()
        return super().validate(attrs)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.image:
            request = self.context.get('request')
            if request:
                data['image'] = request.build_absolute_uri(instance.image.url)
            else:
                data['image'] = instance.image.url
        else:
            data['image'] = None
        return data


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = '__all__'
        read_only_fields = ['created_at']
