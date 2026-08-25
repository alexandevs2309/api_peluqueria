import logging

from .payment_providers import PaymentProvider
from .cardnet_provider import CardNETProvider
from .stripe_provider import StripePosProvider
from .azul_provider import AzulProvider

logger = logging.getLogger(__name__)


class PaymentProviderFactory:
    """Fábrica que retorna el proveedor de pago POS según el país del tenant.
    
    Lee credenciales per-tenant de BarbershopSettings si existen,
    fallback a env vars / SystemSettings globales.
    """

    PROVIDERS = {
        'DO': AzulProvider,
    }

    DEFAULT_PROVIDER = StripePosProvider

    @classmethod
    def get_provider(cls, tenant, method: str = 'card') -> PaymentProvider:
        if method != 'card':
            raise ValueError(f'No provider for payment method: {method}')

        # 1. Verificar si el tenant tiene un proveedor activo configurado
        provider_class = None
        try:
            from apps.settings_api.barbershop_models import BarbershopSettings
            bs = BarbershopSettings.objects.filter(tenant=tenant).first()
            if bs and bs.active_payment_provider and bs.active_payment_provider != 'manual':
                provider_map = {
                    'cardnet': CardNETProvider,
                    'azul': AzulProvider,
                    'stripe': StripePosProvider,
                }
                provider_class = provider_map.get(bs.active_payment_provider)
        except Exception:
            pass

        # 2. Fallback a country-based routing
        if not provider_class:
            country = getattr(tenant, 'country', None) or 'DEFAULT'
            provider_class = cls.PROVIDERS.get(country, cls.DEFAULT_PROVIDER)

        logger.debug("PaymentProviderFactory: provider=%s tenant=%s", provider_class.__name__, tenant.id)
        return provider_class(tenant=tenant)

    @classmethod
    def register_provider(cls, country_code: str, provider_class):
        cls.PROVIDERS[country_code] = provider_class
        logger.info("PaymentProviderFactory: registered %s for %s", provider_class.__name__, country_code)
