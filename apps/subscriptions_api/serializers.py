from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription, SubscriptionAuditLog

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

class OnboardingSerializer(serializers.Serializer):
    salon_name = serializers.CharField(min_length=3)
    owner_name = serializers.CharField()
    owner_email = serializers.EmailField()
    plan_id = serializers.IntegerField()
    password = serializers.CharField(min_length=8)
    stripe_customer_id = serializers.CharField()
    country = serializers.CharField(required=False, allow_blank=True)

    def validate_owner_email(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if User.objects.filter(email=value).exists():
            raise ValidationError("El email ya está registrado.")
        return value

    def validate_plan_id(self, value):
        if not SubscriptionPlan.objects.filter(id=value, is_active=True).exists():
            raise ValidationError("Plan no válido o inactivo.")
        return value
