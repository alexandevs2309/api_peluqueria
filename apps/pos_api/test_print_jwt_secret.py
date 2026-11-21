"""
Regresión PA-07: el JWT del agente de impresión se firma con una clave DEDICADA,
no con Django SECRET_KEY. Un token firmado con la clave raíz debe ser rechazado
por el agente; aquí se demuestra que el backend nunca lo emite con esa clave.
"""
import jwt
import pytest
from django.conf import settings
from django.test import override_settings

from apps.pos_api.views import SaleViewSet


class _User:
    id = 42
    tenant = None


class _Request:
    user = _User()
    tenant = None


_DEDICATED_SECRET = 'pa07-dedicated-print-secret-with-at-least-32-bytes-of-entropy'


@override_settings(AURON_PRINT_JWT_SECRET=_DEDICATED_SECRET)
def test_print_token_is_signed_with_dedicated_secret():
    response = SaleViewSet().print_token(_Request())

    assert response.status_code == 200
    token = response.data['token']
    payload = jwt.decode(token, _DEDICATED_SECRET, algorithms=['HS256'])
    assert payload['type'] == 'print_agent'
    assert payload['sub'] == '42'

    # La clave raíz de Django NO puede verificar el token del agente.
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])


@override_settings(AURON_PRINT_JWT_SECRET='')
def test_print_token_fails_closed_without_dedicated_secret():
    response = SaleViewSet().print_token(_Request())

    assert response.status_code == 503
    assert 'token' not in response.data
    assert response.data['error'] == 'print_jwt_secret_not_configured'
