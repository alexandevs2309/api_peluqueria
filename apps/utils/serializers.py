"""
Serializers base para documentación OpenAPI profesional
apps/utils/serializers.py
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from typing import Dict, Any


class ErrorResponseSerializer(serializers.Serializer):
    """Respuesta estándar de error."""
    error = serializers.CharField(
        help_text="Descripción del error"
    )
    code = serializers.CharField(
        help_text="Código de error específico",
        required=False
    )
    details = serializers.DictField(
        help_text="Detalles adicionales del error",
        required=False
    )


class ValidationErrorSerializer(serializers.Serializer):
    """Errores de validación de campos."""
    field_errors = serializers.DictField(
        help_text="Errores por campo",
        child=serializers.ListField(child=serializers.CharField())
    )
    non_field_errors = serializers.ListField(
        child=serializers.CharField(),
        help_text="Errores generales",
        required=False
    )


class PaginatedResponseSerializer(serializers.Serializer):
    """Respuesta paginada estándar."""
    count = serializers.IntegerField(
        help_text="Total de registros"
    )
    next = serializers.URLField(
        help_text="URL de la siguiente página",
        allow_null=True
    )
    previous = serializers.URLField(
        help_text="URL de la página anterior", 
        allow_null=True
    )
    results = serializers.ListField(
        help_text="Resultados de la página actual"
    )


class SoftDeleteMixin(serializers.Serializer):
    """Mixin para modelos con soft delete."""
    is_deleted = serializers.BooleanField(
        read_only=True,
        help_text="Indica si el registro está eliminado (soft delete)"
    )
    deleted_at = serializers.DateTimeField(
        read_only=True,
        help_text="Fecha y hora de eliminación",
        allow_null=True
    )


class AuditMixin(serializers.Serializer):
    """Mixin para campos de auditoría."""
    created_at = serializers.DateTimeField(
        read_only=True,
        help_text="Fecha y hora de creación"
    )
    updated_at = serializers.DateTimeField(
        read_only=True,
        help_text="Fecha y hora de última actualización"
    )


class TenantMixin(serializers.Serializer):
    """Mixin para aislamiento multi-tenant."""
    tenant_id = serializers.IntegerField(
        read_only=True,
        help_text="ID del tenant (aislamiento automático)"
    )


@extend_schema_field(serializers.DictField)
class JSONBreakdownField(serializers.JSONField):
    """Campo JSON con estructura documentada para breakdown de cálculos."""
    
    def to_representation(self, value):
        """Representación con estructura clara."""
        if not value:
            return {}
        
        # Asegurar estructura consistente
        return {
            'base_salary': value.get('base_salary', '0.00'),
            'overtime_hours': value.get('overtime_hours', '0.00'),
            'overtime_amount': value.get('overtime_amount', '0.00'),
            'bonuses': value.get('bonuses', '0.00'),
            'deductions': value.get('deductions', '0.00'),
            'gross_total': value.get('gross_total', '0.00'),
            'tax_deductions': value.get('tax_deductions', '0.00'),
            'net_amount': value.get('net_amount', '0.00'),
            'calculation_version': value.get('calculation_version', '1.0'),
        }


class RestoreActionSerializer(serializers.Serializer):
    """Serializer para acción de restaurar registro soft-deleted."""
    success = serializers.BooleanField(
        help_text="Indica si la restauración fue exitosa"
    )
    message = serializers.CharField(
        help_text="Mensaje descriptivo del resultado"
    )


class BulkActionSerializer(serializers.Serializer):
    """Serializer para acciones en lote."""
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="Lista de IDs a procesar",
        min_length=1,
        max_length=100
    )
    
    def validate_ids(self, value):
        """Validar que no haya IDs duplicados."""
        if len(value) != len(set(value)):
            raise serializers.ValidationError("No se permiten IDs duplicados")
        return value