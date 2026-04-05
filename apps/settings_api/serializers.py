from rest_framework import serializers
from .models import Setting, Branch, SystemSettings


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            "id",
            "name",
            "address",
        ]


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
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all(), required=True, allow_null=True)

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
        secret_fields = [
            "smtp_password",
            "stripe_secret_key",
            "webhook_secret",
            "paypal_client_secret",
            "twilio_auth_token",
        ]
        for field in secret_fields:
            if data.get(field):
                data[field] = self.masked_value
        return data
