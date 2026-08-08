"""Tests del endpoint de ingestión de errores del frontend."""
import json

from django.test import TestCase, Client


class TelemetryIngestTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_ingest_batch_ok(self):
        payload = {
            'events': [
                {
                    'severity': 'CRITICAL',
                    'type': 'FATAL',
                    'code': 'INTERNAL_ERROR',
                    'message': 'Algo explotó',
                    'url': '/client/dashboard',
                    'module': 'dashboard',
                    'incident_id': 'ERR-20260806-ABC123',
                    'trace_id': 'trace-1',
                },
                {
                    'severity': 'WARNING',
                    'type': 'NETWORK',
                    'code': 'NETWORK_ERROR',
                    'message': 'Sin conexión',
                    'url': '/pos',
                    'module': 'pos',
                },
            ]
        }
        resp = self.client.post(
            '/api/telemetry/errors/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['received'], 2)

    def test_ingest_ignora_eventos_malformados(self):
        payload = {'events': ['no-soy-dict', {'severity': 'ERROR', 'type': 'X'}]}
        resp = self.client.post(
            '/api/telemetry/errors/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['received'], 1)

    def test_ingest_body_invalido(self):
        resp = self.client.post(
            '/api/telemetry/errors/',
            data='not-json',
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_ingest_sin_campo_events(self):
        resp = self.client.post(
            '/api/telemetry/errors/',
            data=json.dumps({'foo': 'bar'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
