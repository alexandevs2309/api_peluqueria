from rest_framework import serializers
from .models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan
from apps.subscriptions_api.serializers import SubscriptionPlanSerializer

class TenantSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.username", read_only=True)
    subscription_plan_details = SubscriptionPlanSerializer(source="subscription_plan", read_only=True)

    class Meta:
        model = Tenant
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "owner")
    
    def update(self, instance, validated_data):
        print(f"Updating tenant {instance.id} with data: {validated_data}")
        
        # Si se actualiza subscription_plan, actualizar también plan_type
        if 'subscription_plan' in validated_data and validated_data['subscription_plan']:
            plan = validated_data['subscription_plan']
            print(f"Updating plan_type from {instance.plan_type} to {plan.name}")
            validated_data['plan_type'] = plan.name
        
        result = super().update(instance, validated_data)
        print(f"Updated tenant: plan_type={result.plan_type}, subscription_plan={result.subscription_plan}")
        return result
