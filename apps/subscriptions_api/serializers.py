from rest_framework import serializers
from  django.utils.timezone import now
from .models import SubscriptionAuditLog, UserSubscription, SubscriptionPlan

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'
        read_only_fields = ['id','created_at', 'updated_at']

class UserSubscriptionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_display = serializers.SerializerMethodField()

    def get_plan_display(self, obj):
        return obj.plan.get_name_display()
    
    class Meta:
        model = UserSubscription
        fields = [
            'id',
            'user_email',
            'plan',
            'plan_name',
            'plan_display',
            'start_date',
            'end_date',
            'is_active',
        ]
        read_only_fields = [ 'user', 'start_date', 'end_date','is_active']

    def validate(self , data):
        user = self.context['request'].user
        active_sub =UserSubscription.objects.filter(user=user , is_active=True , end_date__gte=now()).exists()

        if active_sub:
            raise serializers.ValidationError('Ya tienes una subscripcion Activa.')
        return data

class SubscriptionAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionAuditLog
        fields = ['id', 'user', 'action', 'description', 'created_at']
        read_only_fields = fields