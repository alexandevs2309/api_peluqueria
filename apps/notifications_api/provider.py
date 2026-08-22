# apps/notifications_api/provider.py
"""Abstraction layer for messaging providers.

Two providers are defined:
- TwilioInternalProvider: for internal platform notifications (SMS, internal WhatsApp if required).
- EvolutionClientProvider: for tenant-scoped WhatsApp messages using Evolution API.

The get_notification_provider function decides which implementation to return based on the
requested context and the tenant configuration.
"""

from typing import Protocol
import os
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class NotificationProvider(Protocol):
    """Protocol that all concrete providers must implement."""

    def send_sms(self, to: str, body: str) -> None:
        """Send an SMS message. Only used by internal provider."""

    def send_whatsapp(self, to: str, template: str, data: dict) -> None:
        """Send a WhatsApp message. Behaviour differs per provider."""


# ---------------------------------------------------------------------------
# Twilio Internal Provider (SMS / internal WhatsApp)
# ---------------------------------------------------------------------------

class TwilioInternalProvider:
    def __init__(self):
        from twilio.rest import Client
        account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None) or os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None) or os.getenv("TWILIO_AUTH_TOKEN")
        if not account_sid or not auth_token:
            raise ImproperlyConfigured("Twilio credentials are missing for internal usage.")
        self.client = Client(account_sid, auth_token)
        self.from_number = getattr(settings, "TWILIO_PHONE_NUMBER", None) or os.getenv("TWILIO_PHONE_NUMBER")

    def send_sms(self, to: str, body: str) -> None:
        logger.info("TwilioInternalProvider: Sending SMS to %s", to)
        self.client.messages.create(body=body, from_=self.from_number, to=to)

    def send_whatsapp(self, to: str, template: str, data: dict) -> None:
        logger.info("TwilioInternalProvider: Sending WhatsApp to %s via template %s", to, template)
        body = template.format(**data)
        self.client.messages.create(body=body, from_=f"whatsapp:{self.from_number}", to=f"whatsapp:{to}")


# ---------------------------------------------------------------------------
# Evolution Client Provider (tenant-scoped WhatsApp)
# ---------------------------------------------------------------------------

class EvolutionClientProvider:
    def __init__(self, barbershop_settings):
        """Initialize with BarbershopSettings instance, not Tenant."""
        self.barbershop_settings = barbershop_settings
        self.tenant = barbershop_settings.tenant
        self.base_url = os.getenv("EVOLUTION_API_URL", "http://localhost:8080").rstrip('/')
        self.token = barbershop_settings.whatsapp_token
        if not self.token:
            raise ImproperlyConfigured("Evolution API token missing for tenant.")

    def _request(self, method: str, path: str, json: dict = None):
        import requests
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.request(method, url, json=json, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def send_sms(self, to: str, body: str) -> None:
        raise NotImplementedError("Evolution API does not support SMS.")

    def send_whatsapp(self, to: str, template: str, data: dict) -> None:
        logger.info("EvolutionClientProvider: Sending WhatsApp to %s for tenant %s", to, self.tenant.id)
        payload = {
            "phone": to,
            "template": template,
            "variables": data,
        }
        self._request("POST", "/messages/whatsapp", json=payload)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_notification_provider(context: str, tenant=None) -> NotificationProvider:
    """Return the appropriate provider.

    * ``context`` can be "internal" or "client".
    * ``tenant`` is required when context == "client".
    """
    if context == "internal":
        return TwilioInternalProvider()
    elif context == "client":
        if tenant is None:
            raise ValueError("Tenant must be provided for client context.")
        # Read from BarbershopSettings, not from Tenant directly
        from apps.settings_api.models import BarbershopSettings
        try:
            barbershop_settings = tenant.barbershop_settings
        except BarbershopSettings.DoesNotExist:
            barbershop_settings = None

        if not barbershop_settings or not barbershop_settings.whatsapp_enabled:
            from apps.audit_api.views import AuditLogViewSet
            AuditLogViewSet.log_integration_error(
                "Evolution",
                f"Tenant {tenant.id} attempted WhatsApp send without Evolution enabled",
            )
            raise Exception("EVOLUTION_NOT_CONFIGURED")

        if not barbershop_settings.whatsapp_token:
            raise Exception("EVOLUTION_NOT_CONFIGURED")

        return EvolutionClientProvider(barbershop_settings)
    else:
        raise ValueError(f"Unknown notification context: {context}")
