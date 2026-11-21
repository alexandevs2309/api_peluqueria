"""
CR-10 / CR-11 — Integración HTTP REAL contra un proveedor local que habla el
protocolo Azul del proyecto (`/vault/create`, `/sales`, `/verify`, `/void`).

NO es el sandbox oficial de Azul: sustituye al proveedor por un servidor HTTP
local para ejercitar el código real de requests/parseo/persistencia sin cargos
ni credenciales reales. Por eso NO permite marcar los hallazgos como VERIFIED;
V-07 y V-08 siguen BLOCKED hasta probar contra el sandbox oficial.

Se omite automáticamente si ya hay un sandbox configurado con otra URL.
"""
import json
import threading
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from apps.payments_api.models import AzulTransaction, Payment, PaymentProvider
from apps.tenants_api.models import Tenant

User = get_user_model()
pytestmark = pytest.mark.django_db(transaction=True)


class _AzulStub(BaseHTTPRequestHandler):
    """Implementa el contrato Azul usado por AzulProvider y AzulService."""

    sales = {}
    calls = []
    lock = threading.Lock()

    def log_message(self, *args):
        pass  # no logear PAN ni secretos

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        payload = json.loads(self.rfile.read(length) or b'{}')
        order = str(payload.get('orderNumber', ''))
        path = self.path

        with self.lock:
            self.calls.append((path, order))

        if path == '/vault/create':
            response = {'responseCode': '00', 'tokenId': f'VAULT-{order or "x"}'}
        elif path == '/sales':
            code = '00'
            if order.endswith('-DEC'):
                code = '51'
            elif order.endswith('-CANCEL'):
                code = '99'
            elif order.endswith('-EXPIRE'):
                code = 'TF'
            elif order.endswith('-PEND'):
                code = '95'
            txn = f'TXN-{order}'
            with self.lock:
                self.sales[order] = {'code': code, 'txn': txn}
            response = {
                'responseCode': code, 'txnNumber': txn,
                'authCode': f'AUTH-{order}', 'IsoResponse': 'Aprobada' if code == '00' else 'Rechazada',
            }
        elif path == '/verify':
            with self.lock:
                record = self.sales.get(order, {'code': '99', 'txn': ''})
            response = {
                'responseCode': record['code'], 'txnNumber': record['txn'],
                'authCode': f'AUTH-{order}', 'IsoResponse': 'ok',
            }
        elif path == '/void':
            response = {'responseCode': '00', 'txnNumber': f'VOID-{order}'}
        else:
            self.send_response(404)
            self.end_headers()
            return

        body = json.dumps(response).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _SystemSettings:
    azul_auth1 = 'AUTH1-TEST'
    azul_auth2 = 'AUTH2-TEST'
    azul_merchant_id = 'MERCHANT-TEST'
    azul_store_id = 'STORE-TEST'
    azul_sandbox = True


class AzulLocalIntegration(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _AzulStub.sales = {}
        _AzulStub.calls = []
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), _AzulStub)
        cls.base_url = f'http://127.0.0.1:{cls.server.server_port}'
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        super().tearDownClass()

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='Azul Local', subdomain='azullocal', is_active=True
        )
        self.user = User.objects.create_user(
            email='azullocal@test.com', password='x', tenant=self.tenant
        )
        self.provider, _ = PaymentProvider.objects.get_or_create(name='azul')
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

        self.settings_patch = patch(
            'apps.settings_api.integration_service.IntegrationService.get_system_settings',
            return_value=_SystemSettings(),
        )
        self.url_patch = patch.dict(
            'apps.payments_api.azul_provider.AZUL_URLS', {'sandbox': self.base_url}
        )

        # AzulService calcula base_url en __init__ desde un literal: se parchea
        # sólo esa configuración, no la lógica HTTP real.
        from apps.payments_api.services import AzulService
        orig_load = AzulService._load_config

        def local_load(instance):
            orig_load(instance)
            instance.base_url = self.base_url

        self.service_patch = patch.object(AzulService, '_load_config', local_load)

        self.settings_patch.start()
        self.url_patch.start()
        self.service_patch.start()
        self.addCleanup(self.settings_patch.stop)
        self.addCleanup(self.url_patch.stop)
        self.addCleanup(self.service_patch.stop)
        _AzulStub.calls.clear()
        _AzulStub.sales.clear()

    def _payload(self, suffix):
        return {
            'order_number': f'ORDER-{suffix}',
            'amount': '19.99',
            'currency': 'DOP',
            'card_number': '4111111111111111',
            'card_expiry': '12/2030',
            'card_cvv': '123',
            'card_holder': 'PRUEBA PRUEBA',
            'idempotency_key': f'key-{suffix}',
        }

    def _charge(self, suffix):
        return self.api.post('/api/payments/azul/card/', self._payload(suffix), format='json')

    def test_full_flow_approved_vault_token_and_persistence(self):
        before = len(_AzulStub.calls)
        response = self._charge('OK')
        assert response.status_code == 200, response.data
        assert response.data['status'] == 'completed'
        assert response.data['txn_number'] == 'TXN-ORDER-OK'

        paths = [p for p, _ in _AzulStub.calls[before:]]
        assert paths == ['/vault/create', '/sales'], paths

        payment = Payment.objects.get(id=response.data['payment_id'])
        assert payment.status == 'completed'
        assert payment.amount == Decimal('19.99') and payment.currency == 'DOP'
        assert '4111111111111111' not in str(payment.metadata)
        assert '123' not in str(payment.metadata)
        attempt = AzulTransaction.objects.get(payment=payment, source='card')
        assert attempt.status == 'completed' and attempt.response_code == '00'

    def test_all_provider_states_reach_the_api(self):
        expected = {
            'DEC': (402, 'failed'),
            'CANCEL': (402, 'cancelled'),
            'EXPIRE': (402, 'expired'),
        }
        for suffix, (http, state) in expected.items():
            response = self._charge(suffix)
            assert response.status_code == http, (suffix, response.data)
            assert response.data['status'] == state, (suffix, response.data)
            assert Payment.objects.filter(tenant=self.tenant, status=state).exists(), (suffix, state)
            attempt = AzulTransaction.objects.filter(source='card', response_code={
                'DEC': '51', 'CANCEL': '99', 'EXPIRE': 'TF'
            }[suffix]).first()
            assert attempt is not None and attempt.status == state, (suffix, attempt)

    def test_replay_does_not_call_provider_twice(self):
        before = len(_AzulStub.calls)
        first = self._charge('REPLAY')
        second = self._charge('REPLAY')
        assert first.status_code == 200 and second.status_code == 200
        assert second.data['idempotent'] is True
        calls = [p for p, _ in _AzulStub.calls[before:]]
        assert calls == ['/vault/create', '/sales'], f'replay cobró dos veces: {calls}'
        assert Payment.objects.filter(tenant=self.tenant).count() == 1

    def test_webhook_end_to_end_verification_duplicates_and_out_of_order(self):
        charge = self._charge('WEBHOOK')
        assert charge.status_code == 200, charge.data
        webhook_body = {
            'responseCode': '00',
            'txnNumber': charge.data['txn_number'],
            'orderNumber': charge.data['order_number'],
            'amount': '1999',  # centavos, como reporta Azul
            'currency': '214',
        }

        def post(payload, auth1='AUTH1-TEST', auth2='AUTH2-TEST'):
            return self.api.post(
                '/api/payments/azul/webhook/', payload, format='json',
                HTTP_AUTH1=auth1, HTTP_AUTH2=auth2,
            )

        ok = post(webhook_body)
        assert ok.status_code == 200, ok.data
        assert ok.json()['received'] is True

        duplicate = post(webhook_body)
        assert duplicate.json().get('duplicate') is True, duplicate.data
        assert AzulTransaction.objects.filter(source='webhook', txn_number=charge.data['txn_number']).count() == 1

        # Replay con orden ajena: se rechaza aunque las credenciales sean válidas.
        forged = post({**webhook_body, 'orderNumber': 'ORDER-OTRO', 'amount': '999999'})
        assert forged.status_code == 404, forged.data

        # Importe distinto: se rechaza antes de llamar a /verify.
        wrong_amount = post({**webhook_body, 'amount': '1'})
        assert wrong_amount.status_code == 400, wrong_amount.data

        # Credenciales inválidas: 401 sin tocar el proveedor.
        unauthorized = post(webhook_body, auth1='MAL')
        assert unauthorized.status_code == 401

        # Fuera de orden: txn válido pero orden anterior también conocido ⇒
        # se valida contra el Payment local y no se marca otro pago como pagado.
        assert Payment.objects.filter(tenant=self.tenant, status='completed').count() == 1
