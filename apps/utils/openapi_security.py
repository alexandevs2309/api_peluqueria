"""
Filtros de seguridad para documentación OpenAPI
apps/utils/openapi_security.py
"""
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import OpenApiExample


class SecureAutoSchema(AutoSchema):
    """Schema que filtra información sensible."""
    
    SENSITIVE_FIELDS = [
        'password', 'token', 'secret', 'key', 'hash',
        'ssn', 'tax_id', 'bank_account', 'credit_card'
    ]
    
    def get_operation(self, path, method):
        """Override para filtrar campos sensibles."""
        operation = super().get_operation(path, method)
        
        # Filtrar ejemplos sensibles
        if 'requestBody' in operation:
            self._sanitize_examples(operation['requestBody'])
            
        if 'responses' in operation:
            for response in operation['responses'].values():
                self._sanitize_examples(response)
                
        return operation
    
    def _sanitize_examples(self, content):
        """Sanitizar ejemplos removiendo datos sensibles."""
        if not isinstance(content, dict):
            return
            
        examples = content.get('content', {}).get('application/json', {}).get('examples', {})
        
        for example in examples.values():
            if 'value' in example:
                self._mask_sensitive_data(example['value'])
    
    def _mask_sensitive_data(self, data):
        """Enmascarar datos sensibles en ejemplos."""
        if isinstance(data, dict):
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                    data[key] = '***HIDDEN***'
                elif isinstance(value, (dict, list)):
                    self._mask_sensitive_data(value)
        elif isinstance(data, list):
            for item in data:
                self._mask_sensitive_data(item)


# Ejemplos seguros para documentación
SAFE_EXAMPLES = {
    'client_example': {
        'name': 'María González',
        'email': 'cliente@ejemplo.com',
        'phone': '+1-809-555-0123',
        'notes': 'Cliente frecuente'
    },
    'employee_example': {
        'name': 'Juan Pérez',
        'email': 'empleado@peluqueria.com',
        'position': 'Estilista Senior',
        'hire_date': '2024-01-15'
    },
    'payroll_example': {
        'employee_id': 123,
        'period_start': '2024-01-01',
        'period_end': '2024-01-31',
        'base_salary': '50000.00',
        'overtime_hours': '8.5'
    },
    'sale_example': {
        'client_id': 456,
        'employee_id': 123,
        'total': '28000.00',
        'payment_method': 'cash',
        'items': [
            {
                'service_id': 1,
                'quantity': 1,
                'unit_price': '25000.00'
            }
        ]
    }
}

# Respuestas de error documentadas
ERROR_EXAMPLES = {
    'unauthorized': OpenApiExample(
        'No autenticado',
        value={'error': 'Token de autenticación requerido'},
        response_only=True
    ),
    'forbidden': OpenApiExample(
        'Sin permisos',
        value={'error': 'No tiene permisos para esta acción'},
        response_only=True
    ),
    'not_found': OpenApiExample(
        'No encontrado',
        value={'error': 'Recurso no encontrado'},
        response_only=True
    ),
    'validation_error': OpenApiExample(
        'Error de validación',
        value={
            'field_errors': {
                'email': ['Este campo es requerido'],
                'phone': ['Formato de teléfono inválido']
            }
        },
        response_only=True
    )
}