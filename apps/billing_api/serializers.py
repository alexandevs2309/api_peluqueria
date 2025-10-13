from rest_framework import serializers
from django.utils import timezone
from .models import Invoice, PaymentAttempt


class PaymentAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAttempt
        fields = "__all__"
        read_only_fields = ["id", "attempted_at"]


class InvoiceSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    tenant_name = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()
    paid_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            "id", "user", "user_email", "user_name", "tenant_name", 
            "subscription", "plan_name", "amount", "description", 
            "due_date", "is_paid", "paid_at", "issued_at", "status"
        ]
        read_only_fields = ["id", "user", "is_paid", "issued_at", "status", "paid_at"]
    
    def get_user_email(self, obj):
        return obj.user.email if obj.user else "Sin usuario"
    
    def get_user_name(self, obj):
        if obj.user:
            return getattr(obj.user, 'full_name', None) or f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return "Sin usuario"
    
    def get_tenant_name(self, obj):
        if obj.user and hasattr(obj.user, 'tenant') and obj.user.tenant:
            return obj.user.tenant.name
        return "Sin tenant"
    
    def get_plan_name(self, obj):
        if obj.subscription and obj.subscription.plan:
            return obj.subscription.plan.get_name_display()
        return "Sin plan"
    
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
