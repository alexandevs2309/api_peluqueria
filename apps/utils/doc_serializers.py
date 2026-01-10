"""
Serializers específicos para documentación OpenAPI
Mejoran la claridad sin afectar la funcionalidad
"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Login exitoso',
            summary='Credenciales válidas',
            description='Ejemplo de login exitoso con tenant',
            value={
                'email': 'admin@peluqueria.com',
                'password': 'password123',
                'tenant_subdomain': 'mi-peluqueria'
            },
            request_only=True,
        ),
    ]
)
class LoginDocSerializer(serializers.Serializer):
    """Autenticación de usuario con tenant"""
    email = serializers.EmailField(
        help_text="Email del usuario registrado"
    )
    password = serializers.CharField(
        help_text="Contraseña del usuario",
        style={'input_type': 'password'}
    )
    tenant_subdomain = serializers.CharField(
        required=False,
        help_text="Subdominio del tenant (opcional para SuperAdmin)"
    )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Respuesta de login',
            summary='Tokens JWT generados',
            description='Tokens de acceso y refresh con información del usuario',
            value={
                'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                'user': {
                    'id': 1,
                    'email': 'admin@peluqueria.com',
                    'full_name': 'Administrador',
                    'role': 'Admin',
                    'tenant': {
                        'id': 1,
                        'name': 'Mi Peluquería',
                        'subdomain': 'mi-peluqueria'
                    }
                }
            },
            response_only=True,
        ),
    ]
)
class LoginResponseDocSerializer(serializers.Serializer):
    """Respuesta exitosa de autenticación"""
    access = serializers.CharField(help_text="Token JWT de acceso (8 horas)")
    refresh = serializers.CharField(help_text="Token JWT de refresh (30 días)")
    user = serializers.DictField(help_text="Información del usuario autenticado")


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Cálculo de nómina',
            summary='Cálculo quincenal completado',
            description='Ejemplo de cálculo de nómina con breakdown detallado',
            value={
                'id': 123,
                'settlement_id': 'calc_2024_01_15_emp_456',
                'employee': 456,
                'employee_name': 'María García',
                'frequency': 'biweekly',
                'period_start': '2024-01-01',
                'period_end': '2024-01-15',
                'status': 'READY',
                'fixed_salary_amount': 15000.00,
                'commission_amount': 3500.00,
                'gross_amount': 18500.00,
                'net_amount': 16150.00,
                'breakdown_available': True
            },
            response_only=True,
        ),
    ]
)
class PayrollCalculationDocSerializer(serializers.Serializer):
    """Cálculo de nómina con información detallada"""
    id = serializers.IntegerField(help_text="ID interno del cálculo")
    settlement_id = serializers.CharField(help_text="ID único del settlement")
    employee = serializers.IntegerField(help_text="ID del empleado")
    employee_name = serializers.CharField(help_text="Nombre completo del empleado")
    frequency = serializers.ChoiceField(
        choices=['biweekly', 'monthly'],
        help_text="Frecuencia de pago"
    )
    period_start = serializers.DateField(help_text="Inicio del período")
    period_end = serializers.DateField(help_text="Fin del período")
    status = serializers.ChoiceField(
        choices=['OPEN', 'READY', 'PAID'],
        help_text="Estado del cálculo: OPEN (en proceso), READY (listo para pago), PAID (pagado)"
    )
    fixed_salary_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Salario fijo del período"
    )
    commission_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Total de comisiones ganadas"
    )
    gross_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Salario bruto (fijo + comisiones)"
    )
    net_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Salario neto (después de deducciones)"
    )
    breakdown_available = serializers.BooleanField(
        help_text="Indica si hay breakdown detallado disponible"
    )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Venta POS completa',
            summary='Venta con servicios y productos',
            description='Ejemplo de venta mixta con múltiples formas de pago',
            value={
                'client': 789,
                'details': [
                    {
                        'content_type': 'service',
                        'object_id': 1,
                        'name': 'Corte de cabello',
                        'quantity': 1,
                        'price': 800.00,
                        'employee_id': 456
                    },
                    {
                        'content_type': 'product',
                        'object_id': 2,
                        'name': 'Shampoo Premium',
                        'quantity': 1,
                        'price': 350.00
                    }
                ],
                'payments': [
                    {
                        'method': 'cash',
                        'amount': 1000.00
                    },
                    {
                        'method': 'card',
                        'amount': 150.00
                    }
                ],
                'discount': 0.00,
                'appointment': 123
            },
            request_only=True,
        ),
    ]
)
class SaleCreateDocSerializer(serializers.Serializer):
    """Crear nueva venta en POS"""
    client = serializers.IntegerField(help_text="ID del cliente")
    details = serializers.ListField(
        child=serializers.DictField(),
        help_text="Lista de servicios/productos vendidos"
    )
    payments = serializers.ListField(
        child=serializers.DictField(),
        help_text="Lista de métodos de pago utilizados"
    )
    discount = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        default=0.00,
        help_text="Descuento aplicado a la venta"
    )
    appointment = serializers.IntegerField(
        required=False,
        help_text="ID de cita asociada (opcional)"
    )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Error de validación',
            summary='Campos requeridos faltantes',
            description='Ejemplo de error cuando faltan campos obligatorios',
            value={
                'detail': 'Validation failed',
                'errors': {
                    'email': ['This field is required.'],
                    'password': ['This field may not be blank.']
                }
            },
            response_only=True,
        ),
    ]
)
class ValidationErrorDocSerializer(serializers.Serializer):
    """Error de validación de campos"""
    detail = serializers.CharField(help_text="Descripción general del error")
    errors = serializers.DictField(
        help_text="Errores específicos por campo",
        child=serializers.ListField(child=serializers.CharField())
    )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Respuesta paginada',
            summary='Lista paginada de recursos',
            description='Estructura estándar para respuestas paginadas',
            value={
                'count': 150,
                'next': 'http://api.example.com/clients/?limit=20&offset=40',
                'previous': 'http://api.example.com/clients/?limit=20&offset=0',
                'results': [
                    {
                        'id': 1,
                        'name': 'Cliente Ejemplo',
                        'email': 'cliente@example.com'
                    }
                ]
            },
            response_only=True,
        ),
    ]
)
class PaginatedResponseDocSerializer(serializers.Serializer):
    """Respuesta paginada estándar"""
    count = serializers.IntegerField(help_text="Total de elementos")
    next = serializers.URLField(
        allow_null=True,
        help_text="URL de la siguiente página (null si es la última)"
    )
    previous = serializers.URLField(
        allow_null=True,
        help_text="URL de la página anterior (null si es la primera)"
    )
    results = serializers.ListField(
        child=serializers.DictField(),
        help_text="Lista de elementos de la página actual"
    )