"""URL pública de reservas, derivada siempre del tenant."""

from django.conf import settings


def public_booking_url(tenant) -> str:
    """Devuelve el enlace canónico de reservas de un negocio.

    El subdomain del tenant es la única fuente de la ruta. ``FRONTEND_URL``
    solo añade el origen absoluto cuando está configurado; nunca se acepta una
    URL elegida por el cliente.
    """
    path = f"/reservar/{tenant.subdomain}"
    base_url = str(getattr(settings, "FRONTEND_URL", "") or "").strip().rstrip("/")
    return f"{base_url}{path}" if base_url else path
