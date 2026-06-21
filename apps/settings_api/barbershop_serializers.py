from rest_framework import serializers
from .barbershop_models import BarbershopSettings


class BarbershopPublicSerializer(serializers.ModelSerializer):
    """
    Serializer para información pública visible por todos los empleados.
    Solo campos necesarios para operación diaria.
    """
    logo = serializers.SerializerMethodField()
    brand_colors = serializers.SerializerMethodField()
    
    name = serializers.CharField(required=False, allow_blank=True)
    primary_color = serializers.CharField(required=False)
    secondary_color = serializers.CharField(required=False)
    accent_color = serializers.CharField(required=False)
    currency = serializers.CharField(required=False)
    currency_symbol = serializers.CharField(required=False)
    
    def get_logo(self, obj):
        return obj.logo.url if obj.logo else None

    def get_brand_colors(self, obj):
        return {
            'primary': obj.primary_color,
            'secondary': obj.secondary_color,
            'accent': obj.accent_color,
        }

    class Meta:
        model = BarbershopSettings
        fields = [
            'name',
            'logo',
            'brand_colors',
            'primary_color',
            'secondary_color',
            'accent_color',
            'currency',
            'currency_symbol',
            'business_hours',
            'contact',
        ]


class BarbershopAdminSerializer(serializers.ModelSerializer):
    """
    Serializer para configuración administrativa.
    Incluye campos financieros y críticos solo para ClientAdmin.
    """
    logo = serializers.SerializerMethodField()
    brand_colors = serializers.SerializerMethodField()
    
    class Meta:
        model = BarbershopSettings
        fields = [
            'name',
            'logo',
            'brand_colors',
            'currency',
            'currency_symbol',
            'business_hours',
            'contact',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_logo(self, obj):
        return obj.logo.url if obj.logo else None

    def get_brand_colors(self, obj):
        return {
            'primary': obj.primary_color,
            'secondary': obj.secondary_color,
            'accent': obj.accent_color,
        }


class BarbershopWriteSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, allow_blank=False)
    business_name = serializers.CharField(required=False, write_only=True, allow_blank=False)

    def validate(self, attrs):
        # Allow 'business_name' as an alias for 'name'
        if 'business_name' in attrs:
            attrs['name'] = attrs.pop('business_name')
        return attrs

    """
    Serializer para escritura (POST/PUT/PATCH).
    Validaciones adicionales para campos críticos.
    """
    class Meta:
        model = BarbershopSettings
        fields = [
            'name',
            'business_name',
            'primary_color',
            'secondary_color',
            'accent_color',
            'currency',
            'currency_symbol',
            'business_hours',
            'contact',
        ]

    def validate_primary_color(self, value):
        return self._validate_hex_color(value, 'primary_color')

    def validate_secondary_color(self, value):
        return self._validate_hex_color(value, 'secondary_color')

    def validate_accent_color(self, value):
        return self._validate_hex_color(value, 'accent_color')

    def _validate_hex_color(self, value, field_name):
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', value):
            raise serializers.ValidationError(f"{field_name} debe ser un color hex válido (ej: #2563EB)")
        return value
    
    def validate_currency(self, value):
        """Validar formato ISO 4217"""
        if len(value) != 3 or not value.isupper():
            raise serializers.ValidationError(
                "Currency must be 3-letter ISO 4217 code (e.g., USD, EUR, DOP)"
            )
        return value
    
    def validate_business_hours(self, value):
        """Validar estructura de horarios"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("business_hours must be a dictionary")
        
        required_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in required_days:
            if day not in value:
                raise serializers.ValidationError(f"Missing day: {day}")
            
            day_data = value[day]
            if not isinstance(day_data, dict):
                raise serializers.ValidationError(f"Invalid format for {day}")
            
            required_keys = ['open', 'close', 'closed']
            if not all(key in day_data for key in required_keys):
                raise serializers.ValidationError(f"Missing keys in {day}: {required_keys}")
        
        return value
