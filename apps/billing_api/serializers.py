from rest_framework import serializers
from django.utils import timezone
from .models import Invoice, PaymentAttempt


class PaymentAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAttempt
        fields = "__all__"
        read_only_fields = ["id", "attempted_at"]


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "user", "subscription", "amount", "description", "due_date", "is_paid", "issued_at", "status"]
        read_only_fields = ["id", "user", "is_paid", "issued_at", "status"]
    
    def validate_amount(self, value):
        """Validar que el monto sea positivo"""
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor a cero")
        return value
    
    def validate_due_date(self, value):
        """Validar que la fecha de vencimiento sea futura"""
        if value <= timezone.now():
            raise serializers.ValidationError("La fecha de vencimiento debe ser futura")
        return value
    
    def validate(self, data):
        """Validaciones adicionales"""
        # Si hay una suscripción, verificar que pertenezca al usuario
        request = self.context.get('request')
        if request and data.get('subscription'):
            if data['subscription'].user != request.user:
                raise serializers.ValidationError("La suscripción no pertenece al usuario actual")
        
        return data
