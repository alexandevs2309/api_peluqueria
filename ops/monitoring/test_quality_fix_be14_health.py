"""BE-14: el health check no debe usar variables sin asignar ni filtrar trazas."""
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection
from django.test import RequestFactory

from ops.monitoring import health_views


def test_quality_fix_be14_health_returns_no_internal_stack():
    factory = RequestFactory()
    fake_inspect = SimpleNamespace(active=lambda: {'worker@host': []})

    with patch.object(health_views.current_app.control, 'inspect', return_value=fake_inspect):
        response = health_views.health_check(factory.get('/ops/health/'))

    payload = json.loads(response.content)
    assert payload['checks']['database']['status'] == 'ok'
    assert payload['checks']['database']['response_time_ms'] >= 0
    assert payload['checks']['redis']['response_time_ms'] >= 0
    assert 'db_start' not in response.content.decode()
    assert 'Traceback' not in response.content.decode()
    assert response.status_code in (200, 503)


def test_quality_fix_be14_health_errors_do_not_expose_internals():
    factory = RequestFactory()
    fake_inspect = SimpleNamespace(active=lambda: {})

    with patch.object(connection, 'cursor', side_effect=RuntimeError('secret /srv/db/password')), \
            patch.object(health_views.current_app.control, 'inspect', return_value=fake_inspect):
        response = health_views.health_check(factory.get('/ops/health/'))

    payload = json.loads(response.content)
    assert payload['checks']['database']['status'] == 'error'
    assert payload['checks']['database']['error'] == 'RuntimeError'
    assert 'secret' not in response.content.decode()
    assert '/srv/' not in response.content.decode()
