import logging
from decimal import Decimal
from typing import Optional

from django.conf import settings

from .payment_providers import PaymentProvider, PaymentResult, PaymentProviderConfig

logger = logging.getLogger(__name__)


class StripePosProvider(PaymentProvider):
    """Wrapper del Stripe existente para pagos POS (default fuera de RD)."""

    def __init__(self, config: PaymentProviderConfig = None):
        self.config = config or self._get_config()

    def _get_config(self) -> PaymentProviderConfig:
        api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
        return PaymentProviderConfig(
            api_key=api_key,
            sandbox='sk_test' in api_key if api_key else True,
            currency='USD',
        )

    def is_available(self) -> bool:
        return bool(self.config.api_key)

    def charge(self, amount: Decimal, currency: str, metadata: dict = None) -> PaymentResult:
        import stripe
        stripe.api_key = self.config.api_key

        metadata = metadata or {}
        amount_cents = int(amount * 100)

        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                metadata={
                    'tenant_id': metadata.get('tenant_id', ''),
                    'user_id': metadata.get('user_id', ''),
                    'source': 'pos',
                },
            )
            return PaymentResult(
                success=True,
                transaction_id=intent.id,
                authorization_code=intent.id[-8:],
                status='pending' if intent.status == 'requires_action' else 'completed',
                amount=amount,
                currency=currency,
                raw_response={'client_secret': intent.client_secret, 'id': intent.id},
            )
        except Exception as e:
            logger.error("Stripe charge error: %s", e)
            return PaymentResult(
                success=False, transaction_id='', authorization_code='',
                status='failed', amount=amount, currency=currency,
                error_message=str(e),
            )

    def refund(self, transaction_id: str, amount: Optional[Decimal] = None) -> PaymentResult:
        import stripe
        stripe.api_key = self.config.api_key

        try:
            kwargs = {'payment_intent': transaction_id}
            if amount is not None:
                kwargs['amount'] = int(amount * 100)
            refund = stripe.Refund.create(**kwargs)
            return PaymentResult(
                success=True,
                transaction_id=refund.id,
                authorization_code=refund.id[-8:],
                status='completed',
                amount=amount or Decimal('0'),
                currency='USD',
            )
        except Exception as e:
            logger.error("Stripe refund error: %s", e)
            return PaymentResult(
                success=False, transaction_id='', authorization_code='',
                status='failed', amount=amount or Decimal('0'), currency='USD',
                error_message=str(e),
            )

    def get_status(self, transaction_id: str) -> str:
        import stripe
        stripe.api_key = self.config.api_key
        try:
            intent = stripe.PaymentIntent.retrieve(transaction_id)
            return intent.status
        except Exception:
            return 'unknown'
