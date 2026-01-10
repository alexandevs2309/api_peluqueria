"""
Estrategia de versionado de API
apps/utils/versioning.py
"""

# REGLAS DE VERSIONADO PARA SAAS PELUQUERÍAS

VERSIONING_RULES = {
    'CUÁNDO_VERSIONAR': [
        'Cambios que rompen contratos existentes',
        'Modificaciones en estructura de respuesta',
        'Eliminación de campos o endpoints'
    ],
    'CUÁNDO_NO_VERSIONAR': [
        'Nuevos campos opcionales',
        'Nuevos endpoints',
        'Bug fixes',
        'Mejoras internas sin impacto'
    ]
}

# ESTRATEGIA ACTUAL
API_STRATEGY = {
    'current': 'v1',
    'max_versions': 2,  # Máximo 2 versiones activas
    'deprecation_period': '6 meses',
    'support_period': '12 meses'
}

# MAPEO DE ENDPOINTS QUE NECESITAN V2
V2_ENDPOINTS = {
    'payroll': {
        'reason': 'Breakdown obligatorio, estructura modificada',
        'breaking_changes': ['breakdown field required', 'response structure changed']
    }
    # Solo agregar endpoints que REALMENTE necesiten v2
}

def should_version(change_type: str) -> bool:
    """Determina si un cambio requiere nueva versión."""
    breaking_changes = [
        'field_removed',
        'field_required', 
        'response_structure_changed',
        'endpoint_removed'
    ]
    return change_type in breaking_changes