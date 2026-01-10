"""
Serializers adicionales para corregir warnings OpenAPI
apps/utils/openapi_serializers.py
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from typing import List, Dict, Any


class EmptyResponseSerializer(serializers.Serializer):
    """Respuesta vacía para endpoints que no retornan datos."""
    pass


class MessageResponseSerializer(serializers.Serializer):
    """Respuesta con mensaje simple."""
    message = serializers.CharField(help_text="Mensaje de respuesta")
    success = serializers.BooleanField(default=True, help_text="Indica si la operación fue exitosa")


class StatsResponseSerializer(serializers.Serializer):
    """Respuesta genérica para estadísticas."""
    total = serializers.IntegerField(help_text="Total de elementos")
    active = serializers.IntegerField(help_text="Elementos activos")
    data = serializers.DictField(help_text="Datos adicionales", required=False)


# Corregir type hints para SerializerMethodField
@extend_schema_field(serializers.CharField)
def get_string_field(self, obj) -> str:
    """Type hint para campos string."""
    return str(obj)


@extend_schema_field(serializers.ListField(child=serializers.CharField()))
def get_list_field(self, obj) -> List[str]:
    """Type hint para campos lista."""
    return []


@extend_schema_field(serializers.DictField)
def get_dict_field(self, obj) -> Dict[str, Any]:
    """Type hint para campos dict."""
    return {}