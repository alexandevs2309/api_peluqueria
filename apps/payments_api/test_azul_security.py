"""
Regresión CR-10 / CR-11: integridad del webhook Azul y flujo real de tarjeta.

CR-10: el webhook actual acepta cualquier ORDER/importe siempre que AUTH1/AUTH2
coincidan y marca el Payment como completado sin verificar con Azul ni
comprobar replay.

CR-11: el checkout envía el importe como float y no existe un endpoint que
tokenice la tarjeta (Data Vault) y cobre con sheating: la UI muestra éxito sin
contraparte real.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.tenants_api.models import Tenant
from apps.payments_api.models import Payment, PaymentProvider

User = get_user_model()


class _SystemSettings:
    azul_auth1 = 'AUTH1-OK'
    azul_auth2 = 'AUTH2-OK'
    azul_merchant_id = 'MERCHANT'
    azul_store_id = 'STORE'
    azul_sandbox = True


@pytest.mark.django_db
class TestAzulWebhookIntegrity(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Azul', subdomain='azulsec', is_active=True)
        self.user = User.objects.create_user(
            email='azul@test.com', password='p', tenant=self.tenant
        )
        self.provider, _ = PaymentProvider.objects.get_or_create(name='azul')
        self.payment = Payment.objects.create(
            tenant=self.tenant, user=self.user, provider=self.provider,
            amount=Decimal('1500.00'), currency='DOP', status='pending',
            provider_payment_id='TXN-VALID',
            metadata={'azul_order_number': 'ORDER-VALID'},
        )
        self.client = APIClient()

    def _post_webhook(self, payload, auth1='AUTH1-OK', auth2='AUTH2-OK'):
        return self.client.post(
            '/api/payments/azul/webhook/', payload, format='json',
            HTTP_AUTH1=auth1, HTTP_AUTH2=auth2,
        )

    def test_webhook_with_mismatched_order_does_not_complete_payment(self):
        """Un atacante con AUTH1/AUTH2 no puede completar otro orden."""
        with patch(
            'apps.settings_api.integration_service.IntegrationService.get_system_settings',
            return_value=_SystemSettings(),
        ):
            self._post_webhook({
                'responseCode': '00', 'txnNumber': 'TXN-VALID',
                'orderNumber': 'ORDER-FAKE', 'amount': '999999',
            })
        self.payment.refresh_from_db()
        assert self.payment.status == 'pending', 'Orden falsificada marcó el pago como completado'

    def test_webhook_without_provider_verification_does_not_complete_payment(self):
        """Aun con orden correcto, Azul debe confirmar server-to-server."""
        with patch(
            'apps.settings_api.integration_service.IntegrationService.get_system_settings',
            return_value=_SystemSettings(),
        ), patch(
            'apps.payments_api.services.AzulService.verify_transaction',
            return_value={'success': False, 'response_code': '51', 'txn_number': 'TXN-VALID'},
        ):
            self._post_webhook({
                'responseCode': '00', 'txnNumber': 'TXN-VALID',
                'orderNumber': 'ORDER-VALID', 'amount': '150000',
            })
        self.payment.refresh_from_db()
        assert self.payment.status == 'pending', 'Pago completado sin verificación de Azul'

    def test_webhook_rejected_when_credentials_are_wrong(self):
        with patch(
            'apps.settings_api.integration_service.IntegrationService.get_system_settings',
            return_value=_SystemSettings(),
        ):
            response = self._post_webhook(
                {'responseCode': '00', 'txnNumber': 'TXN-VALID', 'orderNumber': 'ORDER-VALID'},
                auth1='WRONG',
            )
        assert response.status_code == 401

    def test_webhook_rejected_when_credentials_are_not_configured(self):
        """Fase 4: sin AUTH1/AUTH2 configurados el webhook debe fallar cerrado.

        Con las credenciales esperadas vacías, un atacante podía enviar las
        cabeceras también vacías y superar la primera capa.
        """
        from types import SimpleNamespace

        unconfigured = SimpleNamespace(
            azul_auth1='',
            azul_auth2='',
            azul_merchant_id='MERCHANT',
            azul_store_id='STORE',
            azul_sandbox=True,
        )
        with patch(
            'apps.settings_api.integration_service.IntegrationService.get_system_settings',
            return_value=unconfigured,
        ), patch(
            'apps.payments_api.services.AzulService.verify_transaction'
        ) as verify:
            response = self._post_webhook(
                {'responseCode': '00', 'txnNumber': 'TXN-VALID', 'orderNumber': 'ORDER-VALID'},
                auth1='', auth2='',
            )
        assert response.status_code == 401
        verify.assert_not_called()
        self.payment.refresh_from_db()
        assert self.payment.status == 'pending'


@pytest.mark.django_db
class TestAzulCardAmountType(TestCase):
    def test_checkout_result_amount_is_decimal(self):
        """CR-11: ningún importe de Azul debe viajar como float."""
        from apps.payments_api.services import AzulService

        with patch.object(AzulService, '_post', return_value={
            'responseCode': '00', 'txnNumber': 'TXN-1', 'authCode': 'AUTH',
        }):
            result = AzulService().create_checkout_sale(
                order_number='ORDER-1', amount=Decimal('19.99'), currency='DOP'
            )
        assert isinstance(result['amount'], Decimal), f"amount es {type(result['amount'])}"


@pytest.mark.django_db
class TestAzulCardFlow(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='Azul Card', subdomain='azulcard', is_active=True)
        self.user = User.objects.create_user(
            email='card@test.com', password='p', tenant=self.tenant
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.payload = {
            'order_number': 'ORDER-CARD-1',
            'amount': '19.99',
            'currency': 'DOP',
            'card_number': '4111111111111111',
            'card_expiry': '12/2030',
            'card_cvv': '123',
            'card_holder': 'PRUEBA PRUEBA',
            'idempotency_key': 'card-key-1',
        }

    def _provider(self, status='completed', success=True):
        from unittest.mock import MagicMock
        from apps.payments_api.payment_providers import PaymentResult
        provider = MagicMock()
        provider.is_configured = True
        provider.create_vault_token.return_value = {'success': True, 'token_id': 'TOKEN-1'}
        provider.charge_with_vault.return_value = PaymentResult(
            success=success, transaction_id='TXN-CARD-1', authorization_code='AUTH-1',
            status=status, amount=Decimal('19.99'), currency='DOP',
            raw_response={'responseCode': '00' if success else '51'},
        )
        return provider

    def test_card_payment_approved_without_persisting_pan(self):
        provider = self._provider()
        with patch('apps.payments_api.views.AzulProvider', return_value=provider):
            response = self.client.post('/api/payments/azul/card/', self.payload, format='json')

        assert response.status_code == 200, response.data
        assert response.data['status'] == 'completed'
        payment = Payment.objects.get(id=response.data['payment_id'])
        assert payment.status == 'completed'
        assert '4111111111111111' not in str(payment.metadata)
        assert '123' not in str(payment.metadata)
        assert response.data['amount'] == '19.99'

    def test_card_payment_declined_is_failed_not_success(self):
        provider = self._provider(status='failed', success=False)
        with patch('apps.payments_api.views.AzulProvider', return_value=provider):
            response = self.client.post('/api/payments/azul/card/', self.payload, format='json')

        assert response.status_code == 402
        assert response.data['status'] == 'failed'
        assert Payment.objects.filter(tenant=self.tenant, status='failed').count() == 1

    def test_card_payment_replay_does_not_double_charge(self):
        provider = self._provider()
        with patch('apps.payments_api.views.AzulProvider', return_value=provider):
            first = self.client.post('/api/payments/azul/card/', self.payload, format='json')
            second = self.client.post('/api/payments/azul/card/', self.payload, format='json')

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.data['idempotent'] is True
        assert provider.charge_with_vault.call_count == 1, 'El replay no debe cobrar dos veces'
        assert Payment.objects.filter(tenant=self.tenant).count() == 1
