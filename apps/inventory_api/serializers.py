from rest_framework import serializers
from django.utils.text import slugify
from .models import Product, StockMovement, Supplier

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(required=False, allow_blank=True, max_length=100)
    category = serializers.CharField(default='', allow_blank=True, required=False)
    description = serializers.CharField(default='', allow_blank=True, required=False)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ['tenant']
        
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

        # Generar consecutivo simple por tenant
        for i in range(1, 10000):
            candidate = f"{prefix}-{i:03d}"
            exists = Product.objects.filter(sku=candidate, tenant=tenant)
            if self.instance:
                exists = exists.exclude(pk=self.instance.pk)
            if not exists.exists():
                return candidate

        # Fallback extremadamente improbable
        return f"{prefix}-X001"

    def validate(self, attrs):
        sku = attrs.get('sku', None)

        # Crear: si SKU viene vacío o ausente, generar automáticamente.
        if not self.instance and (sku is None or str(sku).strip() == ''):
            attrs['sku'] = self._generate_sku(attrs)
            return super().validate(attrs)

        # Update sin SKU en payload: conservar SKU actual.
        if self.instance and sku is None:
            return super().validate(attrs)

        # Si SKU se envía explícitamente: normalizar o generar si quedó vacío.
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
