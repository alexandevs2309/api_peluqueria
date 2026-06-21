import os
import logging
from decimal import Decimal
from typing import Optional

import requests
from django.conf import settings

from .payment_providers import PaymentProvider, PaymentResult, PaymentProviderConfig

logger = logging.getLogger(__name__)

CARDNET_URLS = {
    'sandbox': 'https://labservicios.cardnet.com.do/api/payment',
    'production': 'https://ecommerce.cardnet.com.do/api/payment',
}

CARDNET_CURRENCY_CODES = {'DOP': '214', 'USD': '840'}

TRANSACTION_SALE = '0200'
TRANSACTION_REFUND = '0400'

ERROR_MESSAGES = {
    '00': 'Aprobada',
    '01': 'Llamar al Banco',
    '02': 'Llamar al Banco',
    '03': 'Comercio Inválido',
    '04': 'Rechazada',
    '05': 'Rechazada',
    '41': 'Tarjeta Perdida',
    '43': 'Tarjeta Robada',
    '51': 'Fondos Insuficientes',
    '54': 'Tarjeta Vencida',
    '57': 'Transacción No Permitida',
    '61': 'Excede Límite de Monto',
    '62': 'Tarjeta Restringida',
    '91': 'Banco Emisor Fuera de Línea',
    'TF': 'Autenticación 3DS Falló',
}


class CardNETProvider(PaymentProvider):
    """Pagos presenciales vía CardNET para República Dominicana."""

    def __init__(self, config: PaymentProviderConfig = None):
        self.config = config or self._load_config()

    def _load_config(self) -> PaymentProviderConfig:
        return PaymentProviderConfig(
            merchant_id=os.getenv('CARDNET_MERCHANT_ID', ''),
            terminal_id=os.getenv('CARDNET_TERMINAL_ID', ''),
            api_key=os.getenv('CARDNET_API_KEY', ''),
            sandbox=os.getenv('CARDNET_SANDBOX', 'true').lower() == 'true',
            currency='DOP',
        )

    def _base_url(self) -> str:
        env = 'sandbox' if self.config.sandbox else 'production'
        return CARDNET_URLS[env]

    def _headers(self) -> dict:
        return {
            'Content-Type': 'application/json',
        }

    def is_available(self) -> bool:
        return bool(self.config.merchant_id and self.config.terminal_id)

    def charge(self, amount: Decimal, currency: str, metadata: dict = None) -> PaymentResult:
        metadata = metadata or {}
        currency_code = CARDNET_CURRENCY_CODES.get(currency.upper(), '214')
        amount_cents = int(amount * 100)
        tax_cents = int(amount * Decimal('0.18') * 100)
        order_id = metadata.get('order_id', '')
        transaction_id = metadata.get('transaction_id', '')

        payload = {
            'TransactionType': TRANSACTION_SALE,
            'CurrencyCode': currency_code,
            'AcquiringInstitutionCode': self.config.merchant_id[:3],
            'MerchantType': '7230',
            'MerchantNumber': self.config.merchant_id,
            'MerchantTerminal': self.config.terminal_id,
            'Amount': str(amount_cents).zfill(12),
            'Tax': str(tax_cents).zfill(12),
            'MerchantName': (metadata.get('business_name') or 'Auron Suite')[:40],
            'OrdenId': str(order_id),
            'TransactionId': str(transaction_id)[:6].zfill(6),
        }

        try:
            logger.info(
                "CardNET charge amount=%s currency=%s merchant=%s",
                amount, currency, self.config.merchant_id,
            )
            resp = requests.post(
                f"{self._base_url()}/transactions",
                json=payload,
                headers=self._headers(),
                timeout=30,
            )
        except requests.RequestException as e:
            logger.error("CardNET charge network error: %s", e)
            return PaymentResult(
                success=False, transaction_id='', authorization_code='',
                status='failed', amount=amount, currency=currency,
                error_message=f'Error de conexión con CardNET: {str(e)}',
            )

        if resp.status_code not in (200, 201):
            logger.warning(
                "CardNET charge failed status=%s body=%s",
                resp.status_code, resp.text,
            )
            return PaymentResult(
                success=False, transaction_id='', authorization_code='',
                status='failed', amount=amount, currency=currency,
                error_message=f'CardNET respondió con estado {resp.status_code}',
            )

        data = resp.json()
        response_code = data.get('response-code', '99')
        pn_ref = data.get('pnRef') or data.get('id') or ''
        approval_code = data.get('approval-code') or ''

        if response_code == '00':
            logger.info("CardNET charge approved ref=%s code=%s", pn_ref, approval_code)
            return PaymentResult(
                success=True,
                transaction_id=pn_ref,
                authorization_code=approval_code,
                status='completed',
                amount=amount,
                currency=currency,
                raw_response=data,
            )

        logger.warning("CardNET charge denied code=%s ref=%s", response_code, pn_ref)
        return PaymentResult(
            success=False,
            transaction_id=pn_ref,
            authorization_code='',
            status='failed',
            amount=amount,
            currency=currency,
            error_message=ERROR_MESSAGES.get(response_code, f'Código {response_code}'),
            raw_response=data,
        )

    def refund(self, transaction_id: str, amount: Optional[Decimal] = None) -> PaymentResult:
        payload = {
            'TransactionType': TRANSACTION_REFUND,
            'MerchantNumber': self.config.merchant_id,
            'MerchantTerminal': self.config.terminal_id,
            'token': transaction_id,
            'idempotency-key': f'refund-{transaction_id}',
            'environment': 'Ecommerce',
        }

        try:
            resp = requests.post(
                f"{self._base_url()}/transactions/voids",
                json=payload,
                headers=self._headers(),
                timeout=30,
            )
        except requests.RequestException as e:
            logger.error("CardNET refund network error: %s", e)
            return PaymentResult(
                success=False, transaction_id='', authorization_code='',
                status='failed', amount=Decimal('0'), currency='DOP',
                error_message=str(e),
            )

        data = resp.json()
        response_code = data.get('response-code', '99')
        return PaymentResult(
            success=response_code == '00',
            transaction_id=data.get('pnRef', ''),
            authorization_code=data.get('approval-code', ''),
            status='completed' if response_code == '00' else 'failed',
            amount=amount or Decimal('0'),
            currency='DOP',
            raw_response=data,
        )

    def get_status(self, transaction_id: str) -> str:
        return 'unknown'
