from rest_framework import serializers
from .models import Product, StockMovement, Supplier

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
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
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        print(f"Product {instance.name} - Image field: {instance.image}")
        if instance.image:
            request = self.context.get('request')
            if request:
                image_url = request.build_absolute_uri(instance.image.url)
                print(f"Image URL: {image_url}")
                data['image'] = image_url
            else:
                data['image'] = instance.image.url
        else:
            data['image'] = None
            print("No image found")
        print(f"Final data: {data}")
        return data

class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = '__all__'
        read_only_fields = ['created_at']
