from rest_framework.views import exception_handler
from rest_framework.response import Response

# @deprecated: No está registrado en settings.py EXCEPTION_HANDLER.
# Se mantiene por compatibilidad. Eliminar después de verificar que ningún
# código externo lo importa (p.ej. desde scripts o migraciones).
# Reemplazo: rest_framework.views.exception_handler (default de DRF).
def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        custom_response = {
            'error': str(exc),
            'details': response.data,
            'status_code': response.status_code
        }
        return Response(custom_response, status=response.status_code)
    return response