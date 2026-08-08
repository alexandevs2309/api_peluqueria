"""Tests para AzulProvider y AzulService."""
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from apps.payments_api.azul_provider import AzulProvider, PaymentProviderConfig


@pytest.fixture
def azul_config():
    return PaymentProviderConfig(
        merchant_id='MERCHANT001',
        terminal_id='STORE001',
        api_key='auth1_val',
        webhook_secret='auth2_val',
        sandbox=True,
        currency='DOP',
    )


class TestAzulProvider:
    def test_is_available_returns_false_when_not_configured(self):
        provider = AzulProvider(PaymentProviderConfig())
        assert provider.is_available() is False
        assert provider.is_configured is False

    def test_is_available_returns_true_when_configured(self, azul_config):
        provider = AzulProvider(azul_config)
        assert provider.is_available() is True
        assert provider.is_configured is True

    def test_base_url_sandbox(self, azul_config):
        provider = AzulProvider(azul_config)
        assert 'sandbox' in provider._base_url()

    def test_base_url_production(self, azul_config):
        azul_config.sandbox = False
        provider = AzulProvider(azul_config)
        assert 'sandbox' not in provider._base_url()

    @patch('apps.payments_api.azul_provider.requests.post')
    def test_charge_success(self, mock_post, azul_config):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'responseCode': '00',
                'txnNumber': 'TXN123456',
                'authCode': 'AUTH789',
            }
        )
        provider = AzulProvider(azul_config)
        result = provider.charge(
            amount=Decimal('100.00'),
            currency='DOP',
            metadata={'order_number': 'ORD-001', 'tenant_id': '1'},
        )
        assert result.success is True
        assert result.transaction_id == 'TXN123456'
        assert result.authorization_code == 'AUTH789'
        assert result.status == 'completed'

    @patch('apps.payments_api.azul_provider.requests.post')
    def test_charge_declined(self, mock_post, azul_config):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'responseCode': '51',
                'IsoResponse': 'Fondos insuficientes',
                'txnNumber': 'TXN999',
            }
        )
        provider = AzulProvider(azul_config)
        result = provider.charge(
            amount=Decimal('500.00'),
            currency='DOP',
            metadata={'order_number': 'ORD-002'},
        )
        assert result.success is False
        assert 'Fondos insuficientes' in result.error_message

    @patch('apps.payments_api.azul_provider.requests.post')
    def test_charge_network_error(self, mock_post, azul_config):
        from requests.exceptions import ConnectionError
        mock_post.side_effect = ConnectionError('Connection refused')
        provider = AzulProvider(azul_config)
        result = provider.charge(Decimal('100.00'), 'DOP')
        assert result.success is False
        assert 'Error de conexión' in result.error_message

    @patch('apps.payments_api.azul_provider.requests.post')
    def test_create_vault_token_success(self, mock_post, azul_config):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'responseCode': '00',
                'tokenId': 'VAULT_TOKEN_123',
            }
        )
        provider = AzulProvider(azul_config)
        result = provider.create_vault_token(
            card_number='4111111111111111',
            card_expiry='12/28',
            customer_email='test@example.com',
        )
        assert result['success'] is True
        assert result['token_id'] == 'VAULT_TOKEN_123'

    @patch('apps.payments_api.azul_provider.requests.post')
    def test_charge_with_vault_success(self, mock_post, azul_config):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'responseCode': '00',
                'txnNumber': 'TXN_RECUR_001',
                'authCode': 'AUTH_RECUR',
            }
        )
        provider = AzulProvider(azul_config)
        result = provider.charge_with_vault(
            token_id='VAULT_TOKEN_123',
            amount=Decimal('29.99'),
            currency='DOP',
            order_number='SUB-RECUR-001',
        )
        assert result.success is True
        assert result.transaction_id == 'TXN_RECUR_001'

    @patch('apps.payments_api.azul_provider.requests.post')
    def test_refund_success(self, mock_post, azul_config):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'responseCode': '00',
                'txnNumber': 'REFUND_TXN_001',
            }
        )
        provider = AzulProvider(azul_config)
        result = provider.refund(transaction_id='TXN123456')
        assert result.success is True

    def test_get_status_mapping(self, azul_config):
        provider = AzulProvider(azul_config)
        assert provider.get_status('some_txn') in ('completed', 'failed', 'pending')
