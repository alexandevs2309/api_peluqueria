
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.appointments_api.models import Appointment
from .models import Sale, SaleDetail, Payment, CashRegister, CashCount, Promotion, Receipt, PosConfiguration, NCFSequence, Coupon
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
        fields = ['id', 'method', 'amount', 'provider_transaction_id']

class SaleSerializer(serializers.ModelSerializer):
    details = SaleDetailSerializer(many=True)
    payments = PaymentSerializer(many=True)
    appointment = serializers.PrimaryKeyRelatedField(queryset=Appointment.objects.none(), required=False)
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    employee_name = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    coupon = serializers.PrimaryKeyRelatedField(queryset=Coupon.objects.none(), required=False, allow_null=True)

    class Meta:
        model = Sale
        fields = [
            'id', 'branch', 'client', 'client_name', 'employee_name', 'user', 'user_name', 
            'date_time', 'total', 'discount', 'paid', 'payment_method', 'closed', 'details', 
            'payments', 'appointment', 'points_earned', 'points_redeemed',
            'ncf', 'ncf_type', 'rnc', 'company_name',
            'promotion', 'promotion_name',
            'coupon', 'coupon_code',
        ]
        read_only_fields = [
            'user', 'user_name', 'date_time', 'closed', 'client_name', 'employee_name', 
            'points_earned', 'points_redeemed', 'ncf', 'promotion_name', 'coupon_code',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            tenant = getattr(request, 'tenant', None)
            if tenant:
                # Scoped: only appointments belonging to this tenant
                from django.db.models import Q
                self.fields['appointment'].queryset = Appointment.objects.filter(
                    Q(client__tenant=tenant) | Q(stylist__tenant=tenant)
                )
                from apps.clients_api.models import Client
                from apps.settings_api.models import Branch
                self.fields['client'].queryset = Client.objects.filter(tenant=tenant)
                self.fields['branch'].queryset = Branch.objects.filter(tenant=tenant)
                self.fields['promotion'].queryset = Promotion.objects.filter(tenant=tenant)
                self.fields['coupon'].queryset = Coupon.objects.filter(tenant=tenant)
            elif request.user.is_superuser:
                # Superuser without tenant scope sees all (admin/global context)
                self.fields['appointment'].queryset = Appointment.objects.all()
                from apps.clients_api.models import Client
                from apps.settings_api.models import Branch
                self.fields['client'].queryset = Client.objects.all()
                self.fields['branch'].queryset = Branch.objects.all()
                self.fields['promotion'].queryset = Promotion.objects.all()
                self.fields['coupon'].queryset = Coupon.objects.all()
            else:
                # No tenant - no access
                self.fields['appointment'].queryset = Appointment.objects.none()
                from apps.clients_api.models import Client
                from apps.settings_api.models import Branch
                self.fields['client'].queryset = Client.objects.none()
                self.fields['branch'].queryset = Branch.objects.none()
                self.fields['promotion'].queryset = Promotion.objects.none()
                self.fields['coupon'].queryset = Coupon.objects.none()

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
        
        # Validaciones específicas de NCF para República Dominicana
        ncf_type = data.get('ncf_type')
        if ncf_type:
            # Validar que sea un tipo válido
            valid_types = [t[0] for t in NCFSequence.COMPROBANTE_TYPES]
            if ncf_type not in valid_types:
                raise serializers.ValidationError({
                    'ncf_type': _('Invalid NCF type.')
                })
            
            if ncf_type == '01':
                rnc = (data.get('rnc') or '').strip()
                company_name = (data.get('company_name') or '').strip()
                if not rnc:
                    raise serializers.ValidationError({
                        'rnc': _('RNC is required for Fiscal Credit (B01) invoices.')
                    })
                if not company_name:
                    raise serializers.ValidationError({
                        'company_name': _('Company name is required for Fiscal Credit (B01) invoices.')
                    })
                # Validar RNC en RD: 9 o 11 dígitos numéricos
                import re
                if not re.match(r'^\d{9}$|^\d{11}$', rnc):
                    raise serializers.ValidationError({
                        'rnc': _('Invalid RNC. Must be exactly 9 or 11 digits.')
                    })
        
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

        # Validar coupon pertenece al tenant
        coupon = data.get('coupon')
        if coupon and hasattr(coupon, 'tenant_id'):
            if coupon.tenant_id != tenant.id:
                raise serializers.ValidationError({
                    'coupon': _('Coupon does not belong to your tenant')
                })
            
        return data

    def create(self, validated_data):
        details_data = validated_data.pop('details')
        payments_data = validated_data.pop('payments')
        user = self.context['request'].user
        validated_data['user'] = user

        appointment = validated_data.pop('appointment', None)
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
        fields = ['id', 'user', 'user_name', 'branch', 'opened_at', 'closed_at', 'initial_cash', 'final_cash', 'is_open', 'sales_amount']
        read_only_fields = ['user', 'user_name', 'opened_at', 'closed_at', 'sales_amount']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            tenant = getattr(request, 'tenant', None)
            if tenant:
                from apps.settings_api.models import Branch
                from django.contrib.auth import get_user_model
                User = get_user_model()
                self.fields['branch'].queryset = Branch.objects.filter(tenant=tenant)
                self.fields['user'].queryset = User.objects.filter(tenant=tenant)
    
    def get_sales_amount(self, obj):
        """Calcular ventas en efectivo asociadas a esta sesión de caja"""
        if not obj.opened_at:
            return 0.0
        return obj.sales_amount

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
        fields = ['id', 'tenant', 'user', 'business_name', 'address', 'phone', 'email', 'website', 'rnc',
                 'currency', 'currency_symbol', 'tax_rate', 'tax_included',
                 'receipt_template', 'receipt_footer', 'auto_print_receipt', 'require_customer',
                 'allow_negative_stock']
        read_only_fields = ['tenant', 'user']


class NCFSequenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NCFSequence
        fields = [
            'id', 'tenant', 'type', 'prefix', 'start_sequence', 
            'end_sequence', 'current_sequence', 'expiration_date', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['tenant', 'created_at', 'updated_at']

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'description', 'type', 'value', 'min_purchase_amount',
            'start_date', 'end_date', 'is_active', 'max_uses', 'current_uses'
        ]
        read_only_fields = ['current_uses']

    def validate_code(self, value):
        return value.strip().upper()

    def validate(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("La fecha de inicio debe ser anterior a la de finalización.")
        return data

class CouponValidationSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    cart_total = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0.00)

    def validate_code(self, value):
        return value.strip().upper()
