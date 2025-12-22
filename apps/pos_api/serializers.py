
from rest_framework import serializers
from django.db import transaction
from decimal import Decimal

from apps.appointments_api.models import Appointment
from .models import Sale, SaleDetail, Payment, CashRegister, CashCount, Promotion, Receipt, PosConfiguration
from apps.inventory_api.models import Product, StockMovement
from .tenant_utils import validate_tenant_ownership
from .state_validators import SaleStateValidator



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
    client_name = serializers.CharField(source='client.name', read_only=True)
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)

    class Meta:
        model = Sale
        fields = ['id', 'client', 'client_name', 'employee_name', 'user', 'date_time', 'total', 'discount', 'paid', 'payment_method', 'closed', 'details', 'payments' , 'appointment']
        read_only_fields = ['user', 'date_time', 'closed', 'client_name', 'employee_name']
    
    def to_representation(self, instance):
        # OPTIMIZACIÓN: Usar datos precargados en lugar de queries adicionales
        data = super().to_representation(instance)
        
        # Solo agregar employee_name si está precargado
        if hasattr(instance, 'employee') and instance.employee:
            if hasattr(instance.employee, 'user'):
                data['employee_name'] = instance.employee.user.full_name or instance.employee.user.email
            else:
                data['employee_name'] = 'Empleado'
        else:
            data['employee_name'] = None
            
        return data

    def validate(self, data):
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Validating sale data: {data}")
        
        # Validar que existan details y payments
        if not data.get('details'):
            raise serializers.ValidationError("Se requiere al menos un detalle de venta")
        if not data.get('payments'):
            raise serializers.ValidationError("Se requiere al menos un método de pago")
        
        # VALIDACIONES CRÍTICAS DE NEGOCIO
        total_details = Decimal('0')
        total_payments = Decimal('0')
        
        for detail in data.get('details', []):
            quantity = Decimal(str(detail.get('quantity', 0)))
            price = Decimal(str(detail.get('price', 0)))
            
            # Validar rangos
            if quantity <= 0 or quantity > 1000:
                raise serializers.ValidationError("Cantidad debe ser entre 1 y 1000")
            if price < 0 or price > 100000:
                raise serializers.ValidationError("Precio debe ser entre 0 y 100,000")
            
            total_details += quantity * price
        
        for payment in data.get('payments', []):
            amount = Decimal(str(payment.get('amount', 0)))
            if amount < 0:
                raise serializers.ValidationError("Monto de pago no puede ser negativo")
            total_payments += amount
        
        # Validar que pagos cubran el total
        discount = Decimal(str(data.get('discount', 0)))
        if discount < 0:
            raise serializers.ValidationError("Descuento no puede ser negativo")
        
        total_with_discount = total_details - discount
        if total_payments < total_with_discount:
            raise serializers.ValidationError("Pagos insuficientes para cubrir el total")
            
        return data

    @transaction.atomic
    def create(self, validated_data):
        details_data = validated_data.pop('details')
        payments_data = validated_data.pop('payments')
        user = self.context['request'].user
        validated_data['user'] = user

        # VALIDAR TENANT
        if not user.tenant:
            raise serializers.ValidationError("Usuario sin tenant asignado")

        appointment = validated_data.get('appointment')
        
        # Validar appointment pertenece al tenant
        if appointment:
            validate_tenant_ownership(user, client=appointment.client)
        
        # Validar estado inicial
        initial_status = validated_data.get('status', 'completed')
        SaleStateValidator.validate_state(initial_status)
        
        sale = Sale.objects.create(**validated_data)

        # Crear detalles y pagos
        for detail in details_data:
            # Convertir content_type string a ContentType object
            from django.contrib.contenttypes.models import ContentType
            if detail['content_type'] == 'service':
                content_type = ContentType.objects.get(app_label='services_api', model='service')
            else:  # product
                content_type = ContentType.objects.get(app_label='inventory_api', model='product')
            
            detail['content_type'] = content_type
            obj = SaleDetail.objects.create(sale=sale, **detail)
            
            # Lógica de stock para productos con concurrencia segura
            if obj.content_type.model == 'product':
                try:
                    # Validar que object_id sea un entero válido
                    object_id = int(obj.object_id)
                    if object_id <= 0 or object_id > 999999:
                        raise ValueError("ID inválido")
                    
                    # CONCURRENCIA: select_for_update
                    product = Product.objects.select_for_update().get(id=object_id)
                    
                    # Validar tenant ownership si el producto tiene tenant
                    if hasattr(product, 'tenant'):
                        validate_tenant_ownership(user, product=product)
                    
                except (Product.DoesNotExist, ValueError, TypeError):
                    raise serializers.ValidationError("Producto no encontrado o ID inválido")
                
                if product.stock < obj.quantity:
                    raise serializers.ValidationError(
                        f"Stock insuficiente para {product.name}. "
                        f"Disponible: {product.stock}, solicitado: {obj.quantity}"
                    )
                
                # Actualizar stock
                product.stock -= obj.quantity
                product.save()
                
                StockMovement.objects.create(
                    product=product,
                    quantity=-obj.quantity,
                    reason=f"Venta #{sale.id} - {obj.quantity} unidades"
                )

        for payment in payments_data:
            Payment.objects.create(sale=sale, **payment)

        # ✅ Si existe appointment, cambiar estado a 'completed' y guardar (validación mejorada)
        if appointment and isinstance(appointment, Appointment):
            # Validar estados permitidos
            allowed_statuses = ["completed", "cancelled", "no_show"]
            new_status = "completed"
            if new_status not in allowed_statuses:
                raise serializers.ValidationError("Estado de cita inválido")
            appointment.status = new_status
            appointment.sale = sale
            appointment.save(update_fields=['status', 'sale'])
            
            # Marcar que la venta puede generar earnings
            if sale.status == 'completed':
                sale.earnings_generated = False  # Permitir generación
                sale.save(update_fields=['earnings_generated'])

        return sale

class CashRegisterSerializer(serializers.ModelSerializer):
    sales_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = CashRegister
        fields = ['id', 'user', 'opened_at', 'closed_at', 'initial_cash', 'final_cash', 'is_open', 'sales_amount']
        read_only_fields = ['user', 'opened_at', 'closed_at', 'sales_amount']
    
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
            return Decimal('0.00')
        if value < 0 or value > 1000000:
            raise serializers.ValidationError("Efectivo inicial debe ser entre 0 y 1,000,000")
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
        if value < 0 or value > 1000000:
            raise serializers.ValidationError("Efectivo final debe ser entre 0 y 1,000,000")
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
        fields = ['id', 'user', 'currency', 'currency_symbol', 'tax_rate', 'tax_included',
                 'receipt_template', 'receipt_footer', 'auto_print_receipt', 'require_customer',
                 'allow_negative_stock']
        read_only_fields = ['user']