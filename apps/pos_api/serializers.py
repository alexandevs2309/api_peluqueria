
from rest_framework import serializers

from apps.appointments_api.models import Appointment
from .models import Sale, SaleDetail, Payment, CashRegister
from apps.inventory_api.models import Product, StockMovement



class SaleDetailSerializer(serializers.ModelSerializer):
    item_type = serializers.SerializerMethodField()
    
    class Meta:
        model = SaleDetail
        fields = ['id', 'content_type', 'object_id', 'name', 'quantity', 'price', 'item_type']
        
    def get_item_type(self, obj):
        return obj.content_type.model

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'method', 'amount']

class SaleSerializer(serializers.ModelSerializer):
    details = SaleDetailSerializer(many=True)
    payments = PaymentSerializer(many=True)
    appointment = serializers.PrimaryKeyRelatedField(queryset=Appointment.objects.all(), required=False)
    client_name = serializers.CharField(source='client.name', read_only=True)

    class Meta:
        model = Sale
        fields = ['id', 'client', 'client_name', 'user', 'date_time', 'total', 'discount', 'paid', 'payment_method', 'closed', 'details', 'payments' , 'appointment']
        read_only_fields = ['user', 'date_time', 'closed', 'client_name']

    def validate(self, data):
        total_calculated = sum(d['quantity'] * d['price'] for d in data['details']) - data.get('discount', 0)
        paid_total = sum(p['amount'] for p in data['payments'])

        if round(total_calculated, 2) != round(data['total'], 2):
            raise serializers.ValidationError("El total no coincide con el cálculo de los detalles.")
        if round(paid_total, 2) != round(data['paid'], 2):
            raise serializers.ValidationError("La suma de los pagos no coincide con el valor pagado.")
        return data

    def create(self, validated_data):
        details_data = validated_data.pop('details')
        payments_data = validated_data.pop('payments')
        user = self.context['request'].user
        validated_data['user'] = user

        appointment = validated_data.get('appointment')
        sale = Sale.objects.create(**validated_data)

        # Crear detalles y pagos
        for detail in details_data:
            obj = SaleDetail.objects.create(sale=sale, **detail)
            # Lógica de stock para productos
            if obj.content_type == 'product':
                try:
                    product = Product.objects.get(id=obj.object_id)
                except Product.DoesNotExist:
                    raise serializers.ValidationError(f"Producto con ID {obj.object_id} no encontrado.")
                if product.stock < obj.quantity:
                    raise serializers.ValidationError(f"Stock insuficiente para el producto {product.name}. Stock actual: {product.stock}, cantidad solicitada: {obj.quantity}.")
                product.stock -= obj.quantity
                product.save()
                StockMovement.objects.create(
                    product=product,
                    quantity=-obj.quantity,
                    reason=f"Venta de {obj.quantity} unidades de {product.name}"
                )

        for payment in payments_data:
            Payment.objects.create(sale=sale, **payment)

        # ✅ Si existe appointment, cambiar estado a 'completed' y guardar
        if appointment:
            appointment.status = "completed"
            appointment.sale = sale
            appointment.save()

        return sale

class CashRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashRegister
        fields = ['id', 'user', 'opened_at', 'closed_at', 'initial_cash', 'final_cash', 'is_open']
        read_only_fields = ['user', 'opened_at', 'closed_at']