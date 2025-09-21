from rest_framework import serializers
from .models import Setting, SettingAuditLog, Branch, SystemSettings

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            "id",
            "name",
            "address",
        ]

class SettingSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(required=True )
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
                    f"Formato inválido para {day}. Ejemplo: '9:00-18:00'"
                )
        return value

class SettingExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        exclude = ["id", "created_at", "updated_at", "logo"]

class SettingAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SettingAuditLog
        fields = [
            "id",
            "setting",
            "changed_by",
            "changed_at",
            "change_summary",
        ]

class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = [
            "id",
            # Configuración General
            "platform_name",
            "support_email",
            # Configuración de Clientes
            "max_tenants",
            "trial_days",
            "default_currency",
            # Configuración de Plataforma
            "platform_domain",
            "supported_languages",
            "platform_commission_rate",
            # Límites por Plan
            "basic_plan_max_employees",
            "premium_plan_max_employees",
            "enterprise_plan_max_employees",
            # Integraciones Globales
            "stripe_enabled",
            "paypal_enabled",
            "twilio_enabled",
            "sendgrid_enabled",
            "aws_s3_enabled",
            # Preferencias del Sistema
            "maintenance_mode",
            "email_notifications",
            "auto_suspend_expired",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
