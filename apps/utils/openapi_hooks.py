"""
Hooks de postprocesamiento para OpenAPI
apps/utils/openapi_hooks.py
"""

def filter_internal_endpoints(result, generator, request, public):
    """Filtrar endpoints internos del schema."""
    paths_to_remove = []
    
    for path, path_item in result.get('paths', {}).items():
        # Filtrar endpoints admin
        if '/admin/' in path:
            paths_to_remove.append(path)
        # Filtrar endpoints de debug
        elif '/debug/' in path or '/test/' in path:
            paths_to_remove.append(path)
    
    for path in paths_to_remove:
        result['paths'].pop(path, None)
    
    return result


def add_common_responses(result, generator, request, public):
    """Agregar respuestas comunes a todos los endpoints."""
    common_responses = {
        '401': {
            'description': 'No autenticado',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'error': {'type': 'string'}
                        }
                    }
                }
            }
        },
        '403': {
            'description': 'Sin permisos',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'error': {'type': 'string'}
                        }
                    }
                }
            }
        }
    }
    
    # Agregar respuestas comunes a endpoints que requieren auth
    for path, path_item in result.get('paths', {}).items():
        for method, operation in path_item.items():
            if method in ['get', 'post', 'put', 'patch', 'delete']:
                if 'security' in operation or 'security' in result:
                    operation.setdefault('responses', {}).update(common_responses)
    
    return result


def clean_operation_ids(result, generator, request, public):
    """Limpiar operation IDs duplicados."""
    operation_ids = set()
    
    for path, path_item in result.get('paths', {}).items():
        for method, operation in path_item.items():
            if method in ['get', 'post', 'put', 'patch', 'delete']:
                operation_id = operation.get('operationId')
                if operation_id:
                    # Si está duplicado, agregar sufijo
                    if operation_id in operation_ids:
                        counter = 1
                        new_id = f"{operation_id}_{counter}"
                        while new_id in operation_ids:
                            counter += 1
                            new_id = f"{operation_id}_{counter}"
                        operation['operationId'] = new_id
                        operation_ids.add(new_id)
                    else:
                        operation_ids.add(operation_id)
    
    return result