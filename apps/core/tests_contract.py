"""Tests del contrato de error estándar (apps.core.exceptions_handler).

Cubre: shape estándar por error_type, retro-compatibilidad con bodies ad-hoc,
incident_id solo en FATAL/5xx, trace_id presente, y no exponer stack traces.
"""
import pytest
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.test import APIRequestFactory
from rest_framework import exceptions as drf_exceptions

from apps.core.exceptions import (
    ApiErrorException,
    BusinessError,
    ValidationError,
    PermissionError,
    AuthenticationError,
    NotFoundError,
    SubscriptionError,
    RateLimitError,
)


def _response_for(exception_cls, **kwargs):
    class ProbeView(APIView):
        permission_classes = []

        def get(self, request, *args, **kwargs):
            raise exception_cls(**kwargs)

    request = APIRequestFactory().get('/probe/')
    return ProbeView.as_view()(request)


# --- Tests ---

class TestContractShape:
    @pytest.mark.parametrize('exc_cls,expected_type,expected_status', [
        (ValidationError, 'VALIDATION', 400),
        (BusinessError, 'BUSINESS', 422),
        (PermissionError, 'PERMISSION', 403),
        (AuthenticationError, 'AUTHENTICATION', 401),
        (NotFoundError, 'NOT_FOUND', 404),
        (SubscriptionError, 'BUSINESS', 402),
        (RateLimitError, 'RATE_LIMIT', 429),
    ])
    def test_typed_exception_shape(self, exc_cls, expected_type, expected_status):
        response = _response_for(exc_cls)
        body = response.data

        assert response.status_code == expected_status
        assert isinstance(body, dict)
        assert body['type'] == expected_type
        assert isinstance(body['code'], str) and body['code']
        assert isinstance(body['message'], str) and body['message']
        assert isinstance(body['details'], dict)
        assert 'timestamp' in body
        assert 'severity' in body
        assert 'origin' in body
        # No expone stack traces ni internals
        assert 'traceback' not in str(body)
        assert 'exc_info' not in str(body)

    def test_incident_id_solo_en_fatal(self):
        business = _response_for(BusinessError)
        assert 'incident_id' not in business.data

        class BoomError(ApiErrorException):
            status_code = 500
            error_type = 'FATAL'

        fatal = _response_for(BoomError)
        assert 'incident_id' in fatal.data
        assert fatal.data['incident_id'].startswith('ERR-')
        assert fatal.data['severity'] == 'CRITICAL'

    def test_trace_id_requiere_request_id(self):
        from django.test import override_settings

        class ProbeView(APIView):
            permission_classes = []
            def get(self, request, *args, **kwargs):
                raise BusinessError('ups')

        request = APIRequestFactory().get('/probe/')
        request.request_id = 'abc-trace-123'
        response = ProbeView.as_view()(request)
        assert response.data['trace_id'] == 'abc-trace-123'


class TestRetroCompatibility:
    def test_body_con_code_propio_se_reutiliza(self):
        class LegacyView(APIView):
            permission_classes = []
            def get(self, request, *args, **kwargs):
                raise drf_exceptions.ValidationError({
                    'code': 'NO_TENANT',
                    'error': 'No tenant assigned',
                    'action_required': 'contact_admin',
                })

        response = LegacyView.as_view()(APIRequestFactory().get('/probe/'))
        body = response.data
        assert response.status_code == 400
        assert body['code'] == 'NO_TENANT'
        assert body['type'] == 'VALIDATION'
        assert body['details']['action_required'] == 'contact_admin'

    def test_drf_validation_por_campo(self):
        class LegacyView(APIView):
            permission_classes = []
            def get(self, request, *args, **kwargs):
                raise drf_exceptions.ValidationError({'email': ['campo requerido']})

        response = LegacyView.as_view()(APIRequestFactory().get('/probe/'))
        body = response.data
        assert body['type'] == 'VALIDATION'
        assert body['details']['email'] == ['campo requerido']
        assert body['message']  # mensaje genérico legible


class TestMiddlewareContract:
    def test_headers_trace_y_incident(self):
        from apps.utils.middleware import ErrorContextMiddleware
        from django.http import JsonResponse

        class Req:
            pass

        request = Req()
        request.request_id = 'trace-1'
        response = JsonResponse({'code': 'NO_TENANT', 'error': 'x'}, status=403)
        out = ErrorContextMiddleware(lambda r: response).process_response(request, response)
        assert out['X-Trace-Id'] == 'trace-1'

    def test_middleware_normaliza_ad_hoc(self):
        from apps.utils.middleware import ErrorContextMiddleware
        from django.http import JsonResponse

        class Req:
            pass

        request = Req()
        request.request_id = 'trace-2'
        response = JsonResponse({'code': 'TRIAL_EXPIRED', 'error': 'Trial expired'}, status=402)
        out = ErrorContextMiddleware(lambda r: response).process_response(request, response)
        import json as _json
        body = _json.loads(out.content)
        assert body['code'] == 'TRIAL_EXPIRED'  # retro: se conserva
        assert body['type'] == 'BUSINESS'
        assert body['severity'] == 'WARNING'
        assert body['origin'] == 'Subscription'
        assert body['timestamp']
        assert body['trace_id'] == 'trace-2'

    def test_5xx_sin_incident_genera_header(self):
        from apps.utils.middleware import ErrorContextMiddleware
        from django.http import JsonResponse

        class Req:
            pass

        request = Req()
        request.request_id = 'trace-3'
        response = JsonResponse({'detail': 'boom'}, status=500)
        out = ErrorContextMiddleware(lambda r: response).process_response(request, response)
        assert out['X-Incident-Id'].startswith('ERR-')
