from rest_framework import serializers
from .models import Setting, Branch, SystemSettings, SECRET_FIELDS


class BranchSerializer(serializers.ModelSerializer):
    employee_count = serializers.SerializerMethodField()
    is_main = serializers.BooleanField(default=False)

    class Meta:
        model = Branch
        fields = [
            "id",
            "name",
            "address",
            "is_main",
            "is_active",
            "employee_count",
        ]
        read_only_fields = ["employee_count"]

    def get_employee_count(self, obj):
        return obj.branch_employees.count() if hasattr(obj, 'branch_employees') else 0


class BranchWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "name", "address", "is_main", "is_active"]

    def validate(self, attrs):
        request = self.context.get("request")
        if request:
            tenant = getattr(request, "tenant", None) or getattr(request.user, "tenant", None)
            if tenant:
                # Restricción si es una sucursal nueva (no modificación)
                if not self.instance:
                    plan = tenant.subscription_plan
                    if plan and not plan.allows_multiple_branches:
                        active_branches = Branch.objects.filter(tenant=tenant, is_active=True).count()
                        if active_branches >= 1:
                            raise serializers.ValidationError(
                                "Tu plan actual no permite crear múltiples sucursales. "
                                "Por favor, mejora tu plan a Business o Enterprise."
                            )

                if attrs.get("is_main"):
                    existing_main = Branch.objects.filter(tenant=tenant, is_main=True)
                    if self.instance:
                        existing_main = existing_main.exclude(pk=self.instance.pk)
                    if existing_main.exists():
                        raise serializers.ValidationError(
                            {"is_main": "Ya existe una sucursal principal"}
                        )
        return attrs


class SettingSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(required=True)
    business_email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    address = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    currency = serializers.CharField(required=False)
    tax_percentage = serializers.DecimalField(required=False, max_digits=5, decimal_places=2)
    timezone = serializers.CharField(required=False)
    business_hours = serializers.JSONField(required=False)
    preferences = serializers.JSONField(required=False)
    logo = serializers.ImageField(required=False, allow_null=True)
    theme = serializers.CharField(required=False)
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.none(), required=True, allow_null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            tenant = getattr(request, 'tenant', None)
            if tenant:
                self.fields['branch'].queryset = Branch.objects.filter(tenant=tenant)

    class Meta:
        model = Setting
        fields = [
            "id",
            "branch",
            "business_name",
            "business_email",
            "phone_number",
            "address",
            "currency",
            "tax_percentage",
            "timezone",
            "business_hours",
            "preferences",
            "logo",
            "theme",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_business_hours(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("El horario debe ser un diccionario.")
        for day, hours in value.items():
            if not isinstance(hours, str) or "-" not in hours:
                raise serializers.ValidationError(
                    f"Formato invalido para {day}. Ejemplo: '9:00-18:00'"
                )
        return value


class SettingExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        exclude = ["id", "created_at", "updated_at", "logo"]


class SystemSettingsSerializer(serializers.ModelSerializer):
    masked_value = "configured"

    class Meta:
        model = SystemSettings
        fields = [
            "id",
            # General
            "platform_name",
            "support_email",
            # Clientes
            "max_tenants",
            "trial_days",
            "default_currency",
            # Plataforma
            "platform_domain",
            "supported_languages",
            "platform_commission_rate",
            # Limites por Plan
            "basic_plan_max_employees",
            "premium_plan_max_employees",
            "enterprise_plan_max_employees",
            # Integraciones Globales
            "stripe_enabled",
            "paypal_enabled",
            "twilio_enabled",
            "sendgrid_enabled",
            "aws_s3_enabled",
            # Email (SMTP)
            "smtp_host",
            "smtp_port",
            "smtp_username",
            "smtp_password",
            "from_email",
            "from_name",
            # Stripe
            "stripe_public_key",
            "stripe_secret_key",
            "webhook_secret",
            # PayPal
            "paypal_client_id",
            "paypal_client_secret",
            "paypal_sandbox",
            # Twilio
            "twilio_account_sid",
            "twilio_auth_token",
            "twilio_phone_number",
            # Preferencias
            "maintenance_mode",
            "email_notifications",
            "auto_suspend_expired",
            "auto_upgrade_limits",
            # Seguridad
            "jwt_expiry_minutes",
            "max_login_attempts",
            "login_lockout_minutes",
            "password_min_length",
            "require_email_verification",
            "enable_mfa",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in SECRET_FIELDS:
            if data.get(field):
                data[field] = self.masked_value
        return data

    def to_internal_value(self, data):
        # track which secret fields were sent as sentinel
        self._secret_sentinels = {}
        for field in SECRET_FIELDS:
            if field in data and data[field] == self.masked_value:
                self._secret_sentinels[field] = True
        return super().to_internal_value(data)

    def update(self, instance, validated_data):
        for field in SECRET_FIELDS:
            if field in validated_data and field in getattr(self, '_secret_sentinels', {}):
                validated_data.pop(field)
        return super().update(instance, validated_data)
