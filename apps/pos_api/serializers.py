
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.appointments_api.models import Appointment
from .models import Sale, SaleDetail, Payment, CashRegister, CashCount, Promotion, Receipt, PosConfiguration
from apps.inventory_api.models import Product, StockMovement



class SaleDetailSerializer(serializers.ModelSerializer):
    item_type = serializers.SerializerMethodField()
    # Field to specify the type of content ('service' or 'product')
    content_type = serializers.CharField(help_text="Type of item being sold (service/product)")
    
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
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    employee_name = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ['id', 'client', 'client_name', 'employee_name', 'user', 'user_name', 'date_time', 'total', 'discount', 'paid', 'payment_method', 'closed', 'details', 'payments' , 'appointment']
        read_only_fields = ['user', 'user_name', 'date_time', 'closed', 'client_name', 'employee_name']

    def get_employee_name(self, obj):
        employee_user = getattr(getattr(obj, 'employee', None), 'user', None)
        return getattr(employee_user, 'full_name', None) or getattr(employee_user, 'email', None)

    def get_user_name(self, obj):
        return getattr(getattr(obj, 'user', None), 'full_name', None) or getattr(getattr(obj, 'user', None), 'email', None)

    def validate(self, data):
        import logging
        logger = logging.getLogger(__name__)
        logger.debug("Validating sale payload")
        
        # Validar que existan details y payments
        if not data.get('details'):
            raise serializers.ValidationError("Se requiere al menos un detalle de venta")
        if not data.get('payments'):
            raise serializers.ValidationError("Se requiere al menos un método de pago")
        
        # Validación cross-tenant
        request = self.context.get('request')
        if not request:
            return data
        
        tenant = getattr(request, 'tenant', None)
        
        # SuperAdmin puede relacionar cualquier objeto
        if request.user.is_superuser:
            return data
        
        # Usuario sin tenant no puede crear ventas
        if not tenant:
            raise serializers.ValidationError(_('User without assigned tenant'))
        
        # Validar appointment pertenece al tenant
        appointment = data.get('appointment')
        if appointment:
            # Appointment no tiene tenant directo, validar via client o stylist
            from django.db.models import Q
            valid_appointment = Appointment.objects.filter(
                Q(client__tenant_id=tenant.id) | Q(stylist__tenant_id=tenant.id),
                id=appointment.id
            ).exists()
            
            if not valid_appointment:
                raise serializers.ValidationError({
                    'appointment': _('Appointment does not belong to your tenant')
                })
        
        # Validar client pertenece al tenant
        client = data.get('client')
        if client and hasattr(client, 'tenant_id'):
            if client.tenant_id != tenant.id:
                raise serializers.ValidationError({
                    'client': _('Client does not belong to your tenant')
                })
            
        return data

    def create(self, validated_data):
        details_data = validated_data.pop('details')
        payments_data = validated_data.pop('payments')
        user = self.context['request'].user
        validated_data['user'] = user

        appointment = validated_data.get('appointment')
        sale = Sale.objects.create(**validated_data)

        # Crear detalles
        for detail in details_data:
            # Convertir content_type string a ContentType object
            from django.contrib.contenttypes.models import ContentType
            if detail['content_type'] == 'service':
                content_type = ContentType.objects.get(app_label='services_api', model='service')
            else:  # product
                content_type = ContentType.objects.get(app_label='inventory_api', model='product')
            
            detail['content_type'] = content_type
            SaleDetail.objects.create(sale=sale, **detail)
            # Stock ya se descuenta en perform_create() con transacciones atómicas

        for payment in payments_data:
            Payment.objects.create(sale=sale, **payment)

        # Si existe appointment, cambiar estado a 'completed'
        if appointment and isinstance(appointment, Appointment):
            allowed_statuses = ["completed", "cancelled", "no_show"]
            new_status = "completed"
            if new_status not in allowed_statuses:
                raise serializers.ValidationError("Estado de cita inválido")
            appointment.status = new_status
            appointment.sale = sale
            appointment.save(update_fields=['status', 'sale'])

        return sale

class CashRegisterSerializer(serializers.ModelSerializer):
    sales_amount = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CashRegister
        fields = ['id', 'user', 'user_name', 'opened_at', 'closed_at', 'initial_cash', 'final_cash', 'is_open', 'sales_amount']
        read_only_fields = ['user', 'user_name', 'opened_at', 'closed_at', 'sales_amount']
    
    def get_sales_amount(self, obj):
        """Calcular ventas del día"""
        from django.db.models import Sum
        from .models import Sale
        
        if not obj.opened_at:
            return 0.0
        
        sales_total = Sale.objects.filter(
            user=obj.user,
            date_time__date=obj.opened_at.date()
        ).aggregate(total=Sum('total'))['total'] or 0
        
        return float(sales_total)

    def get_user_name(self, obj):
        return getattr(getattr(obj, 'user', None), 'full_name', None) or getattr(getattr(obj, 'user', None), 'email', None)

class CashCountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashCount
        fields = ['id', 'cash_register', 'denomination', 'count', 'total', 'created_at']
        read_only_fields = ['total', 'created_at']
    
    def validate(self, data):
        data['total'] = data['denomination'] * data['count']
        return data

class CashRegisterCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear caja registradora"""
    initial_cash = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00, min_value=0)
    
    class Meta:
        model = CashRegister
        fields = ['initial_cash']
    
    def validate_initial_cash(self, value):
        if value is None:
            return 0.00
        return value

class CashRegisterCloseSerializer(serializers.ModelSerializer):
    """Serializer para cerrar caja registradora"""
    final_cash = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    
    class Meta:
        model = CashRegister
        fields = ['final_cash']
    
    def validate_final_cash(self, value):
        if value is None:
            raise serializers.ValidationError("final_cash es requerido para cerrar la caja")
        return value

class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = ['id', 'name', 'description', 'type', 'conditions', 'discount_value', 
                 'min_amount', 'start_date', 'end_date', 'is_active', 'max_uses', 'current_uses']

class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = ['id', 'sale', 'receipt_number', 'template_used', 'generated_at', 
                 'printed_count', 'last_printed']
        read_only_fields = ['receipt_number', 'generated_at']

class PosConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PosConfiguration
        fields = ['id', 'user', 'business_name', 'address', 'phone', 'email', 'website', 'rnc',
                 'currency', 'currency_symbol', 'tax_rate', 'tax_included',
                 'receipt_template', 'receipt_footer', 'auto_print_receipt', 'require_customer',
                 'allow_negative_stock']
        read_only_fields = ['user']
