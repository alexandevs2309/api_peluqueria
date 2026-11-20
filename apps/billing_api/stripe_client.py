"""Configuración central del SDK de Stripe.

El SDK no hereda el ``statement_timeout`` de PostgreSQL: sin un timeout propio,
una degradación de la API externa puede mantener ocupado al worker HTTP/Celery.
"""
import logging

import stripe
from django.conf import settings

logger = logging.getLogger(__name__)


def configure_stripe(api_key=None):
    stripe.api_key = api_key if api_key is not None else settings.STRIPE_SECRET_KEY
    stripe.max_network_retries = 2
    try:
        stripe.default_http_client = stripe.http_client.RequestsClient(timeout=30)
    except Exception:  # pragma: no cover - depende del SDK instalado
        logger.warning("No se pudo configurar el timeout del cliente Stripe")
