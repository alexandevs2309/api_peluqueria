import logging

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

from apps.telemetry_api.models import FrontendErrorEvent

logger = logging.getLogger('api.telemetry')


@csrf_exempt
@require_http_methods(["POST"])
def errors_ingest(request):
    """Ingestión en batch de errores del frontend.

    Body: {"events": [ {severity, type, code, message, url, module, ...}, ... ]}
    Respuesta: {"received": N} — siempre 200 para no generar ruido en el cliente.
    """
    try:
        import json
        body = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    events = body.get('events') if isinstance(body, dict) else None
    if not isinstance(events, list):
        return JsonResponse({'error': 'Field "events" must be a list'}, status=400)

    created = FrontendErrorEvent.ingest_batch(events)
    FrontendErrorEvent.forward_to_sentry(events)

    return JsonResponse({'received': created})
