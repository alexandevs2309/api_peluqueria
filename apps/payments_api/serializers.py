from rest_framework import serializers
from .models import Payment, PaymentProvider

class PaymentProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentProvider
        fields = ['id', 'name', 'is_active']

class PaymentSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.get_name_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'amount', 'currency', 'status', 'provider_name',
            'created_at', 'updated_at', 'completed_at', 'metadata'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']