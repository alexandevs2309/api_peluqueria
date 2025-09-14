from rest_framework import serializers
from .earnings_models import Earning, FortnightSummary

class EarningSerializer(serializers.ModelSerializer):
    fortnight_display = serializers.ReadOnlyField()
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    
    class Meta:
        model = Earning
        fields = [
            'id', 'employee', 'employee_name', 'sale', 'appointment',
            'amount', 'earning_type', 'percentage', 'description',
            'date_earned', 'fortnight_year', 'fortnight_number',
            'fortnight_display', 'created_at'
        ]
        read_only_fields = ['fortnight_year', 'fortnight_number', 'created_at']

class FortnightSummarySerializer(serializers.ModelSerializer):
    fortnight_display = serializers.ReadOnlyField()
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    
    class Meta:
        model = FortnightSummary
        fields = [
            'id', 'employee', 'employee_name', 'fortnight_year', 'fortnight_number',
            'fortnight_display', 'total_earnings', 'total_services', 
            'total_commissions', 'total_tips', 'is_paid', 'paid_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class EarningCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Earning
        fields = [
            'employee', 'sale', 'appointment', 'amount', 
            'earning_type', 'percentage', 'description', 'date_earned'
        ]