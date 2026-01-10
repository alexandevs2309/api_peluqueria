"""
Decoradores OpenAPI para endpoints críticos
apps/utils/openapi_decorators.py
"""
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from apps.utils.serializers import (
    ErrorResponseSerializer, 
    ValidationErrorSerializer,
    RestoreActionSerializer
)


# Respuestas comunes reutilizables
COMMON_RESPONSES = {
    400: OpenApiResponse(
        response=ValidationErrorSerializer,
        description="Errores de validación"
    ),
    401: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="No autenticado - Token requerido",
        examples=[
            OpenApiExample(
                'Token faltante',
                value={'error': 'Token de autenticación requerido'},
                response_only=True
            )
        ]
    ),
    403: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Sin permisos - Acceso denegado",
        examples=[
            OpenApiExample(
                'Sin permisos',
                value={'error': 'No tiene permisos para esta acción'},
                response_only=True
            )
        ]
    ),
    404: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Recurso no encontrado",
        examples=[
            OpenApiExample(
                'No encontrado',
                value={'error': 'Recurso no encontrado'},
                response_only=True
            )
        ]
    ),
}\n\n# Decoradores específicos por dominio\n\ndef payroll_create_schema(request_serializer, response_serializer):\n    \"\"\"Schema para creación de cálculos de nómina.\"\"\"\n    return extend_schema(\n        tags=['payroll'],\n        summary=\"Crear cálculo de nómina\",\n        description=\"\"\"\n        Crea un nuevo cálculo de nómina con breakdown detallado.\n        \n        **Características:**\n        - Cálculo automático basado en reglas configuradas\n        - Breakdown JSON con desglose completo\n        - Versionado para recálculos\n        - Auditoría automática\n        \"\"\",\n        request=request_serializer,\n        responses={\n            201: response_serializer,\n            **COMMON_RESPONSES\n        },\n        examples=[\n            OpenApiExample(\n                'Cálculo básico',\n                value={\n                    'employee_id': 123,\n                    'period_start': '2024-01-01',\n                    'period_end': '2024-01-31',\n                    'base_salary': '50000.00',\n                    'overtime_hours': '8.5'\n                },\n                request_only=True\n            )\n        ]\n    )\n\n\ndef soft_delete_schema(model_name: str):\n    \"\"\"Schema para soft delete.\"\"\"\n    return extend_schema(\n        summary=f\"Eliminar {model_name} (soft delete)\",\n        description=f\"\"\"\n        Elimina el {model_name} usando soft delete.\n        \n        **Importante:**\n        - Los datos NO se eliminan físicamente\n        - Se puede restaurar usando el endpoint /restore/\n        - Se registra auditoría automáticamente\n        \"\"\",\n        responses={\n            204: OpenApiResponse(description=\"Eliminado correctamente\"),\n            **COMMON_RESPONSES\n        }\n    )\n\n\ndef restore_schema(model_name: str):\n    \"\"\"Schema para restaurar registro soft-deleted.\"\"\"\n    return extend_schema(\n        summary=f\"Restaurar {model_name}\",\n        description=f\"\"\"\n        Restaura un {model_name} previamente eliminado (soft delete).\n        \n        **Requisitos:**\n        - El registro debe estar marcado como eliminado\n        - Usuario debe tener permisos de restauración\n        \"\"\",\n        request=None,\n        responses={\n            200: RestoreActionSerializer,\n            **COMMON_RESPONSES\n        },\n        examples=[\n            OpenApiExample(\n                'Restauración exitosa',\n                value={\n                    'success': True,\n                    'message': f'{model_name} restaurado correctamente'\n                },\n                response_only=True\n            )\n        ]\n    )\n\n\ndef pos_sale_schema():\n    \"\"\"Schema específico para ventas POS.\"\"\"\n    return extend_schema(\n        tags=['pos'],\n        summary=\"Registrar venta\",\n        description=\"\"\"\n        Registra una nueva venta en el punto de venta.\n        \n        **Proceso automático:**\n        1. Validación de inventario\n        2. Cálculo de comisiones\n        3. Actualización de stock\n        4. Registro de auditoría\n        \n        **Campos calculados:**\n        - `total`: Suma automática de items\n        - `commission_amount`: Basado en reglas del empleado\n        - `tax_amount`: Según configuración fiscal\n        \"\"\",\n        examples=[\n            OpenApiExample(\n                'Venta con servicios',\n                value={\n                    'client_id': 456,\n                    'employee_id': 123,\n                    'items': [\n                        {\n                            'service_id': 1,\n                            'quantity': 1,\n                            'unit_price': '25000.00'\n                        },\n                        {\n                            'product_id': 5,\n                            'quantity': 2,\n                            'unit_price': '1500.00'\n                        }\n                    ],\n                    'payment_method': 'cash',\n                    'notes': 'Cliente frecuente'\n                },\n                request_only=True\n            )\n        ]\n    )\n\n\ndef auth_login_schema():\n    \"\"\"Schema para login con MFA.\"\"\"\n    return extend_schema(\n        tags=['auth'],\n        summary=\"Iniciar sesión\",\n        description=\"\"\"\n        Autentica usuario y retorna tokens JWT.\n        \n        **Flujo de autenticación:**\n        1. Validación de credenciales\n        2. Verificación MFA (si está habilitado)\n        3. Generación de tokens (access + refresh)\n        4. Registro de auditoría de login\n        \n        **Tokens retornados:**\n        - `access`: Token de acceso (8 horas)\n        - `refresh`: Token de renovación (30 días)\n        \"\"\",\n        examples=[\n            OpenApiExample(\n                'Login básico',\n                value={\n                    'email': 'usuario@peluqueria.com',\n                    'password': 'password123'\n                },\n                request_only=True\n            ),\n            OpenApiExample(\n                'Login con MFA',\n                value={\n                    'email': 'usuario@peluqueria.com',\n                    'password': 'password123',\n                    'mfa_code': '123456'\n                },\n                request_only=True\n            )\n        ]\n    )