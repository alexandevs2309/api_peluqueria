import os
import json
import logging
from decimal import Decimal
from typing import Optional

import requests
from django.conf import settings

from .payment_providers import PaymentProvider, PaymentResult, PaymentProviderConfig
from apps.settings_api.integration_service import IntegrationService

logger = logging.getLogger(__name__)

AZUL_URLS = {
    'sandbox': 'https://sandbox.azul.com.do',
    'production': 'https://azul.com.do',
}

AZUL_SALE_PATH = '/sales'
AZUL_VERIFY_PATH = '/verify'
AZUL_VOID_PATH = '/void'
AZUL_DATAVAULT_PATH = '/vault/create'

AZUL_CURRENCY_CODES = {'DOP': '214', 'USD': '840', 'EUR': '978'}

ERROR_MAP = {
    '00': 'Aprobada',
    '01': 'Llamar al banco emisor',
    '02': 'Llamar al banco emisor',
    '03': 'Comercio inválido',
    '04': 'Rechazada — retener tarjeta',
    '05': 'Rechazada — no honrar',
    '14': 'Tarjeta inválida',
    '41': 'Tarjeta perdida',
    '43': 'Tarjeta robada',
    '51': 'Fondos insuficientes',
    '54': 'Tarjeta vencida',
    '57': 'Transacción no permitida',
    '61': 'Excede límite de monto',
    '62': 'Tarjeta restringida',
    '91': 'Banco emisor fuera de línea',
    'TF': 'Autenticación 3DS falló',
}


class AzulProvider(PaymentProvider):
    """Pagos vía Azul (azul.com.do) para República Dominicana.

    Soporta:
    - Sale (venta directa)
    - Verify (verificación de transacción)
    - Void (anulación/reembolso)
    - Data Vault (tokenización para suscripciones)
    """

    def __init__(self, config: PaymentProviderConfig = None):
        self.config = config or self._load_config()

    def _load_config(self) -> PaymentProviderConfig:
        system = IntegrationService.get_system_settings()
        return PaymentProviderConfig(
            merchant_id=system.azul_merchant_id or os.getenv('AZUL_MERCHANT_ID', ''),
            terminal_id=system.azul_store_id or os.getenv('AZUL_STORE_ID', ''),
            api_key=system.azul_auth1 or os.getenv('AZUL_AUTH1', ''),
            webhook_secret=system.azul_auth2 or os.getenv('AZUL_AUTH2', ''),
            sandbox=getattr(system, 'azul_sandbox', True),
            currency='DOP',
        )

    def _base_url(self) -> str:
        env = 'sandbox' if self.config.sandbox else 'production'
        return AZUL_URLS[env]

    def _auth_params(self) -> dict:
        return {
            'store': self.config.terminal_id,
            'merchant': self.config.merchant_id,
            'auth1': self.config.api_key,
            'auth2': self.config.webhook_secret,
        }

    def _headers(self) -> dict:
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    @property
    def is_configured(self) -> bool:
        return bool(
            self.config.terminal_id
            and self.config.merchant_id
            and self.config.api_key
            and self.config.webhook_secret
        )

    def is_available(self) -> bool:
        return self.is_configured

    def _build_sale_payload(
        self,
        amount: Decimal,
        currency: str,
        order_number: str,
        customer_email: str = '',
        metadata: dict = None,
    ) -> dict:
        metadata = metadata or {}
        currency_code = AZUL_CURRENCY_CODES.get(currency.upper(), '214')
        amount_str = str(int(amount * 100))
        return {
            **self._auth_params(),
            'typeService': 'JSON',
            'orderNumber': order_number[:20],
            'amount': amount_str,
            'currency': currency_code,
            'customerEmail': customer_email or metadata.get('customer_email', ''),
            'customFields': json.dumps({
                'tenant_id': metadata.get('tenant_id', ''),
                'user_id': metadata.get('user_id', ''),
                'plan_id': metadata.get('plan_id', ''),
                'source': metadata.get('source', 'subscription'),
            }),
        }

    def _post(self, path: str, payload: dict, timeout: int = 30) -> dict:
        url = f"{self._base_url()}{path}"
        logger.info(
            "Azul request path=%s store=%s merchant=%s",
            path, self.config.terminal_id, self.config.merchant_id,
        )
        try:
            resp = requests.post(
                url, json=payload, headers=self._headers(), timeout=timeout,
            )
        except requests.RequestException as e:
            logger.error("Azul network error path=%s: %s", path, e)
            return {'success': False, 'error_message': f'Error de conexión con Azul: {str(e)}'}

        if resp.status_code not in (200, 201):
            logger.warning("Azul HTTP %s path=%s body=%s", resp.status_code, path, resp.text[:500])
            return {
                'success': False,
                'responseCode': 'ERR',
                'error_message': f'Azul respondió con estado HTTP {resp.status_code}',
                'raw': resp.text,
            }

        try:
            data = resp.json()
        except (json.JSONDecodeError, ValueError):
            logger.error("Azul invalid JSON path=%s body=%s", path, resp.text[:500])
            return {'success': False, 'responseCode': 'ERR', 'error_message': 'Respuesta inválida de Azul'}

        return data

    def charge(self, amount: Decimal, currency: str, metadata: dict = None) -> PaymentResult:
        metadata = metadata or {}
        order_number = metadata.get('order_number', '')
        if not order_number:
            order_number = f"POS-{metadata.get('tenant_id', '0')[:8]}-{int(__import__('time').time() * 1000) % 100000}"

        payload = self._build_sale_payload(
            amount=amount,
            currency=currency,
            order_number=order_number,
            customer_email=metadata.get('customer_email', ''),
            metadata=metadata,
        )

        data = self._post(AZUL_SALE_PATH, payload)
        return self._parse_response(data, amount, currency)

    def refund(self, transaction_id: str, amount: Optional[Decimal] = None) -> PaymentResult:
        payload = {
            **self._auth_params(),
            'typeService': 'JSON',
            'orderNumber': f"REF-{transaction_id[:12]}",
            'txnNumber': transaction_id,
        }
        if amount is not None:
            payload['amount'] = str(int(amount * 100))

        data = self._post(AZUL_VOID_PATH, payload)
        return self._parse_response(data, amount or Decimal('0'), 'DOP')

    def get_status(self, transaction_id: str) -> str:
        payload = {
            **self._auth_params(),
            'typeService': 'JSON',
            'orderNumber': transaction_id[:20],
            'txnNumber': transaction_id,
        }
        data = self._post(AZUL_VERIFY_PATH, payload)
        response_code = data.get('responseCode', '99')
        if response_code == '00':
            return 'completed'
        if response_code in ('05', '51', '54', '04'):
            return 'failed'
        return 'pending'

    # --- Azul-specific: Data Vault (tokenización para suscripciones) ---

    def create_vault_token(
        self,
        card_number: str,
        card_expiry: str,
        customer_email: str,
        metadata: dict = None,
    ) -> dict:
        """Crear token Data Vault para suscripciones recurrentes.

        Args:
            card_number: PAN de la tarjeta
            card_expiry: MM/YY
            customer_email: email del cliente
            metadata: datos adicionales

        Returns:
            dict con 'tokenId' (vault_token) o 'error_message'
        """
        metadata = metadata or {}
        payload = {
            **self._auth_params(),
            'typeService': 'JSON',
            'cardNumber': card_number,
            'cardExpiry': card_expiry,
            'customerEmail': customer_email,
            'customFields': json.dumps({
                'tenant_id': metadata.get('tenant_id', ''),
                'user_id': metadata.get('user_id', ''),
            }),
        }

        data = self._post(AZUL_DATAVAULT_PATH, payload)
        if data.get('responseCode') == '00' and data.get('tokenId'):
            return {
                'success': True,
                'token_id': data['tokenId'],
                'raw': data,
            }
        return {
            'success': False,
            'error_message': data.get('error_message') or ERROR_MAP.get(
                data.get('responseCode', '99'), f"Error Azul: código {data.get('responseCode', '99')}"
            ),
            'raw': data,
        }

    def charge_with_vault(
        self,
        token_id: str,
        amount: Decimal,
        currency: str,
        order_number: str,
        metadata: dict = None,
    ) -> PaymentResult:
        """Cobrar usando token Data Vault (suscripciones)."""
        metadata = metadata or {}
        currency_code = AZUL_CURRENCY_CODES.get(currency.upper(), '214')
        amount_str = str(int(amount * 100))

        payload = {
            **self._auth_params(),
            'typeService': 'JSON',
            'orderNumber': order_number[:20],
            'amount': amount_str,
            'currency': currency_code,
            'tokenId': token_id,
            'customFields': json.dumps({
                'tenant_id': metadata.get('tenant_id', ''),
                'user_id': metadata.get('user_id', ''),
                'plan_id': metadata.get('plan_id', ''),
                'source': 'recurring',
            }),
        }

        data = self._post(AZUL_SALE_PATH, payload)
        return self._parse_response(data, amount, currency)

    # --- Helpers ---

    def _parse_response(self, data: dict, amount: Decimal, currency: str) -> PaymentResult:
        if data.get('success') is False and data.get('error_message'):
            return PaymentResult(
                success=False, transaction_id='', authorization_code='',
                status='failed', amount=amount, currency=currency,
                error_message=data['error_message'],
                raw_response=data,
            )

        response_code = data.get('responseCode', '99')
        iso_response = data.get('IsoResponse', '')
        txn_number = data.get('txnNumber', '') or data.get('transactionId', '')
        auth_code = data.get('authCode', '') or data.get('authorizationCode', '')

        if response_code == '00':
            logger.info("Azul charge approved txn=%s auth=%s", txn_number, auth_code)
            return PaymentResult(
                success=True,
                transaction_id=txn_number,
                authorization_code=auth_code,
                status='completed',
                amount=amount,
                currency=currency,
                raw_response=data,
            )

        logger.warning("Azul charge denied code=%s iso=%s txn=%s", response_code, iso_response, txn_number)
        return PaymentResult(
            success=False,
            transaction_id=txn_number,
            authorization_code='',
            status='failed',
            amount=amount,
            currency=currency,
            error_message=ERROR_MAP.get(response_code, iso_response or f'Código {response_code}'),
            raw_response=data,
        )
