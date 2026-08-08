# apps/notifications_api/provider.py
"""Abstraction layer for messaging providers.

Two providers are defined:
- TwilioInternalProvider: for internal platform notifications (SMS, internal WhatsApp if required).
- EvolutionClientProvider: for tenant‑scoped WhatsApp messages using Evolution API.

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
        # In internal context we might still need WhatsApp (e.g., alerts). Use classic Twilio API.
        logger.info("TwilioInternalProvider: Sending WhatsApp to %s via template %s", to, template)
        # Simple interpolation – real implementation would map template IDs.
        body = template.format(**data)
        self.client.messages.create(body=body, from_=f"whatsapp:{self.from_number}", to=f"whatsapp:{to}")


# ---------------------------------------------------------------------------
# Evolution Client Provider (tenant‑scoped WhatsApp)
# ---------------------------------------------------------------------------

class EvolutionClientProvider:
    def __init__(self, tenant):
        # tenant is a Django model instance that has evolution_api_enabled and evolution_api_token fields.
        self.tenant = tenant
        self.base_url = os.getenv("EVOLUTION_API_URL", "http://localhost:8080").rstrip('/')
        self.token = tenant.evolution_api_token
        if not self.token:
            raise ImproperlyConfigured("Evolution API token missing for tenant.")

    def _request(self, method: str, path: str, json: dict = None):
        import requests
        url = f"{self.base_url}/{path.lstrip('/') }"
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.request(method, url, json=json, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def send_sms(self, to: str, body: str) -> None:
        # Evolution API does not support SMS – raise to keep contract.
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
        if not getattr(tenant, "evolution_api_enabled", False):
            # Log integration error – avoid circular import by lazy import.
            from apps.audit_api.views import AuditLogViewSet
            AuditLogViewSet.log_integration_error(
                "Evolution",
                f"Tenant {tenant.id} attempted WhatsApp send without Evolution enabled",
            )
            raise Exception("EVOLUTION_NOT_CONFIGURED")
        return EvolutionClientProvider(tenant)
    else:
        raise ValueError(f"Unknown notification context: {context}")
