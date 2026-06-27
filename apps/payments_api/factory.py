import logging

from .payment_providers import PaymentProvider
from .cardnet_provider import CardNETProvider
from .stripe_provider import StripePosProvider
from .azul_provider import AzulProvider

logger = logging.getLogger(__name__)


class PaymentProviderFactory:
    """Fábrica que retorna el proveedor de pago POS según el país del tenant."""

    PROVIDERS = {
        'DO': AzulProvider,  # Azul es el procesador primario para RD
    }

    DEFAULT_PROVIDER = StripePosProvider

    @classmethod
    def get_provider(cls, tenant, method: str = 'card') -> PaymentProvider:
        if method != 'card':
            raise ValueError(f'No provider for payment method: {method}')

        country = getattr(tenant, 'country', None) or 'DEFAULT'
        provider_class = cls.PROVIDERS.get(country, cls.DEFAULT_PROVIDER)

        logger.debug("PaymentProviderFactory: country=%s provider=%s", country, provider_class.__name__)
        return provider_class()

    @classmethod
    def register_provider(cls, country_code: str, provider_class):
        cls.PROVIDERS[country_code] = provider_class
        logger.info("PaymentProviderFactory: registered %s for %s", provider_class.__name__, country_code)
