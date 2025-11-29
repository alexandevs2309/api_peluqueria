from rest_framework import serializers
from .earnings_models import Earning, FortnightSummary
from decimal import Decimal

class EarningSerializer(serializers.ModelSerializer):
    fortnight_display = serializers.ReadOnlyField()
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        model = Earning
        fields = [
            'id', 'employee', 'employee_name', 'sale', 'appointment',
            'amount', 'earning_type', 'percentage', 'description',
            'date_earned', 'fortnight_year', 'fortnight_number',
            'fortnight_display', 'created_at'
        ]
        read_only_fields = ['fortnight_year', 'fortnight_number', 'created_at']
    
    def validate_amount(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError("El monto debe ser mayor o igual a 0")
        return value
    
    def validate_percentage(self, value):
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("El porcentaje debe estar entre 0 y 100")
        return value

class FortnightSummarySerializer(serializers.ModelSerializer):
    fortnight_display = serializers.ReadOnlyField()
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    employee_email = serializers.CharField(source='employee.user.email', read_only=True)
    total_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_commissions = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_tips = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        model = FortnightSummary
        fields = [
            'id', 'employee', 'employee_name', 'employee_email', 
            'fortnight_year', 'fortnight_number', 'fortnight_display', 
            'total_earnings', 'total_services', 'total_commissions', 'total_tips', 
            'is_paid', 'paid_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class EarningCreateSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        model = Earning
        fields = [
            'employee', 'sale', 'appointment', 'amount', 
            'earning_type', 'percentage', 'description', 'date_earned'
        ]
    
    def validate_amount(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError("El monto debe ser mayor o igual a 0")
        return value
    
    def validate_percentage(self, value):
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("El porcentaje debe estar entre 0 y 100")
        return value

class EmployeeConfigUpdateSerializer(serializers.Serializer):
    """Serializer para actualizar configuración de empleado"""
    employee_id = serializers.IntegerField(required=True)
    payment_type = serializers.ChoiceField(
        choices=['commission', 'fixed', 'mixed'], 
        required=False
    )
    commission_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, 
        min_value=0, max_value=100, 
        required=False
    )
    fixed_salary = serializers.DecimalField(
        max_digits=10, decimal_places=2, 
        min_value=0, 
        required=False
    )
    
    def validate(self, data):
        payment_type = data.get('payment_type')
        commission_rate = data.get('commission_rate')
        fixed_salary = data.get('fixed_salary')
        
        # Validar que si es tipo 'fixed', tenga fixed_salary
        if payment_type == 'fixed' and not fixed_salary and fixed_salary != 0:
            raise serializers.ValidationError(
                "Para tipo 'fixed' se requiere especificar fixed_salary"
            )
        
        # Validar que si es tipo 'commission', tenga commission_rate
        if payment_type == 'commission' and not commission_rate and commission_rate != 0:
            raise serializers.ValidationError(
                "Para tipo 'commission' se requiere especificar commission_rate"
            )
        
        # Validar que si es tipo 'mixed', tenga ambos
        if payment_type == 'mixed':
            if (not commission_rate and commission_rate != 0) or (not fixed_salary and fixed_salary != 0):
                raise serializers.ValidationError(
                    "Para tipo 'mixed' se requiere especificar commission_rate y fixed_salary"
                )
        
        return data

class EarningsStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas de ganancias"""
    period = serializers.CharField()
    total_generated = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_earned = serializers.DecimalField(max_digits=12, decimal_places=2)
    top_employees = serializers.ListField(child=serializers.DictField())

class PaymentHistorySerializer(serializers.Serializer):
    """Serializer para historial de pagos"""
    employee_id = serializers.IntegerField()
    employee_name = serializers.CharField()
    payment_history = serializers.ListField(child=serializers.DictField())
    total_records = serializers.IntegerField()

class EarningsListResponseSerializer(serializers.Serializer):
    """Serializer para respuesta estandarizada de lista de ganancias"""
    employees = serializers.ListField(child=serializers.DictField())
    summary = serializers.DictField()
    
    def validate_summary(self, value):
        required_fields = ['total_generated', 'total_earned', 'period']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Campo requerido en summary: {field}")
        return value

class MarkPaidRequestSerializer(serializers.Serializer):
    """Serializer para marcar empleado como pagado"""
    period_start = serializers.DateField(format='%Y-%m-%d')
    period_end = serializers.DateField(format='%Y-%m-%d')
    
    def validate(self, data):
        if data['period_start'] > data['period_end']:
            raise serializers.ValidationError(
                "La fecha inicial no puede ser mayor a la fecha final"
            )
        return data