from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription, SubscriptionAuditLog
from apps.subscriptions_api.plan_consistency import get_feature_value

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    features_list = serializers.SerializerMethodField()
    display_name = serializers.CharField(source='get_name_display', read_only=True)
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'display_name', 'description', 'price', 'duration_month', 'stripe_price_id', 'is_active',
            'max_employees', 'max_users', 'allows_multiple_branches', 'features', 'commercial_benefits',
            'features_list', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'name', 'display_name', 'created_at', 'updated_at']
    
    def get_features_list(self, obj):
        """Convert features dict to list for frontend"""
        if not obj.features:
            return []
        if isinstance(obj.features, dict):
            return [key.replace('_', ' ').title() for key, value in obj.features.items() if value]
        return obj.features if isinstance(obj.features, list) else []

class PublicSubscriptionPlanSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source='get_name_display', read_only=True)
    highlight_features = serializers.SerializerMethodField()
    technical_features = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id',
            'name',
            'display_name',
            'description',
            'price',
            'highlight_features',
            'technical_features',
            'commercial_benefits',
        ]

    def get_highlight_features(self, obj):
        highlights = []

        if obj.max_employees == 0:
            highlights.append('Empleados ilimitados')
        else:
            highlights.append(f'Hasta {obj.max_employees} empleados')

        if obj.max_users == 0:
            highlights.append('Usuarios ilimitados')
        else:
            highlights.append(f'Hasta {obj.max_users} usuarios')

        if get_feature_value(obj.features, 'custom_branding', default=False):
            highlights.append('Logo personalizado')
        elif obj.allows_multiple_branches:
            highlights.append('Varias sucursales')
        else:
            highlights.append('1 sucursal')

        return highlights[:3]

    def get_technical_features(self, obj):
        labels = {
            'appointments': 'Agenda de citas organizada',
            'basic_reports': 'Reportes basicos del negocio',
            'cash_register': 'Caja y ventas en un solo lugar',
            'client_history': 'Historial completo de clientes',
            'inventory': 'Control de inventario en tiempo real',
            'advanced_reports': 'Reportes avanzados para tomar decisiones',
            'multi_location': 'Gestion de multiples sucursales',
            'role_permissions': 'Permisos avanzados para el equipo',
            'api_access': 'Acceso a integraciones por API',
            'custom_branding': 'Logo personalizado para tu negocio',
        }
        if not isinstance(obj.features, dict):
            return []
        return [label for key, label in labels.items() if get_feature_value(obj.features, key, default=False)]

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
