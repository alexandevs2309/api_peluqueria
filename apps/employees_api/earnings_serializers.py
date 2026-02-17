from rest_framework import serializers
from decimal import Decimal

# ============================================
# SERIALIZERS DE NÓMINA (PAYROLL)
# ============================================

from .earnings_models import PayrollPeriod, PayrollDeduction, PayrollConfiguration

class PayrollDeductionSerializer(serializers.ModelSerializer):
    deduction_type_display = serializers.CharField(source='get_deduction_type_display', read_only=True)
    
    class Meta:
        model = PayrollDeduction
        fields = ['id', 'deduction_type', 'deduction_type_display', 'amount', 'description', 'is_automatic']


class PayrollPeriodSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    period_display = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    deductions = PayrollDeductionSerializer(many=True, read_only=True)
    
    class Meta:
        model = PayrollPeriod
        fields = [
            'id', 'employee', 'employee_name', 'period_type', 'period_start', 'period_end', 'period_display',
            'status', 'status_display', 'base_salary', 'commission_earnings', 'gross_amount',
            'deductions_total', 'net_amount', 'can_pay', 'pay_block_reason',
            'payment_method', 'payment_reference', 'paid_at', 'deductions'
        ]
        read_only_fields = ['base_salary', 'commission_earnings', 'gross_amount', 'deductions_total', 'net_amount', 'can_pay', 'pay_block_reason']


class PayrollConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollConfiguration
        fields = ['id', 'default_period_type', 'tax_rate', 'social_security_rate', 'health_insurance_rate', 'auto_close_periods']