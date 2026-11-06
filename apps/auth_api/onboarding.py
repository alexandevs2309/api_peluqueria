"""Utilidades de onboarding para el registro de negocios.

Centraliza la generación de enlaces de un solo uso (establecimiento de
contraseña y verificación de correo) y el envío del correo posterior al
commit de la transacción de registro.

Los enlaces de contraseña se basan en ``default_token_generator``:
- No requieren campos adicionales en la base de datos.
- Caducan según ``PASSWORD_RESET_TIMEOUT`` (3 días por defecto).
- Se invalidan automáticamente al cambiar la contraseña (un solo uso).
"""
from __future__ import annotations

import logging
import secrets
import time
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.emails.service import EmailRenderer

logger = logging.getLogger(__name__)


def frontend_base_url() -> str:
    return (getattr(settings, 'FRONTEND_URL', '') or 'http://localhost:4200').rstrip('/')


def email_verification_timeout() -> int:
    return int(getattr(settings, 'EMAIL_VERIFICATION_TIMEOUT', 3 * 24 * 3600))


def generate_email_verification_token() -> str:
    """Token de verificación con expiración incorporada (sin migración)."""
    return f"{int(time.time())}:{secrets.token_urlsafe(32)}"


def is_email_verification_token_valid(token: str) -> bool:
    if not token:
        return False
    if ':' not in token:
        # Compatibilidad con tokens legacy sin expiración incorporada.
        return True
    ts_part, _ = token.split(':', 1)
    try:
        issued_at = int(ts_part)
    except ValueError:
        return False
    return (time.time() - issued_at) <= email_verification_timeout()


def build_uid(user) -> str:
    return urlsafe_base64_encode(force_bytes(user.pk))


def build_set_password_url(user, email: str | None = None) -> str:
    """Enlace de un solo uso para que el propietario cree su contraseña."""
    uid = build_uid(user)
    token = default_token_generator.make_token(user)
    url = f"{frontend_base_url()}/auth/set-password/{uid}/{token}"
    if email:
        url = f"{url}?email={quote(email)}"
    return url


def build_verify_email_url(user) -> str:
    token = getattr(user, 'email_verification_token', None)
    if not token:
        return ''
    url = f"{frontend_base_url()}/auth/verify-email/{token}"
    if user.email:
        url = f"{url}?email={quote(user.email)}"
    return url


def _trial_days(tenant) -> int:
    try:
        from apps.settings_api.models import SystemSettings

        return max(0, int(SystemSettings.get_settings().trial_days or 0))
    except Exception:  # pragma: no cover - defensivo
        return 7


def send_onboarding_email(user, tenant=None, *, set_password_url: str | None = None) -> dict:
    """Envía el correo de bienvenida con enlaces de verificación/contraseña.

    Debe invocarse *después* del commit de la transacción de registro. No
    incluye contraseñas temporales en texto plano.
    """
    from apps.auth_api.tasks import send_email_async

    tenant = tenant or getattr(user, 'tenant', None)
    business_name = getattr(tenant, 'name', '') or 'Auron Suite'
    trial_days = _trial_days(tenant)

    needs_password = not user.has_usable_password()

    # Flujo inequívoco: un solo enlace por correo.
    # - Sin contraseña: enlace de un solo uso que crea la contraseña Y verifica el correo.
    # - Con contraseña: enlace de verificación del correo.
    verify_url = ''
    set_password_url = set_password_url if needs_password else None
    if needs_password:
        if not set_password_url:
            set_password_url = build_set_password_url(user, email=user.email)
    else:
        verify_url = build_verify_email_url(user)

    primary_url = set_password_url or verify_url
    primary_label = 'Crear mi contraseña' if set_password_url else 'Verificar mi correo'

    if not primary_url:
        logger.warning(
            'No onboarding link available for user_id=%s (verified=%s, usable_password=%s)',
            user.pk,
            getattr(user, 'is_email_verified', None),
            user.has_usable_password(),
        )
        return {'email_sent': False, 'recipient': user.email, 'status': 'skipped'}

    subject = f"¡Bienvenido a Auron Suite, {user.full_name or user.email}!"
    text_body = (
        f"Hola {user.full_name or user.email},\n\n"
        f"Tu cuenta para {business_name} ha sido creada exitosamente.\n\n"
        f"Email: {user.email}\n\n"
    )
    if set_password_url:
        text_body += (
            "Crea tu contraseña con este enlace de un solo uso:\n"
            f"{set_password_url}\n\n"
        )
    if verify_url:
        text_body += (
            "También puedes verificar tu correo aquí:\n"
            f"{verify_url}\n\n"
        )
    text_body += (
        "Los enlaces caducan en 3 días y solo pueden usarse una vez.\n\n"
        "El equipo de Auron Suite"
    )

    plan = getattr(tenant, 'subscription_plan', None) if tenant else None
    plan_name = plan.get_name_display() if plan else ''
    html_body = EmailRenderer.render('welcome.html', {
        'business_name': business_name,
        'title': subject,
        'content': (
            f'<p style="margin:0 0 12px;">Hola <strong>{user.full_name or user.email}</strong>,</p>'
            f'<p style="margin:0 0 12px;">Tu cuenta para <strong>{business_name}</strong> está lista.</p>'
        ),
        'user_full_name': user.full_name or user.email,
        'user_email': user.email,
        'tenant_name': business_name,
        'plan_name': plan_name,
        'trial_days': trial_days,
        'trial_end_date': getattr(tenant, 'trial_end_date', None),
        'cta_url': primary_url,
        'cta_label': primary_label,
        'set_password_url': set_password_url,
        'verification_url': verify_url,
        'support_url': getattr(settings, 'SUPPORT_URL', ''),
    })

    try:
        send_email_async.delay(
            subject=subject,
            message=text_body,
            from_email='',
            recipient_list=[user.email],
            html_message=html_body,
        )
    except Exception:  # pragma: no cover - fallo de broker/Celery
        logger.exception(
            'No se pudo encolar el correo de onboarding user_id=%s (Celery no disponible?)',
            user.pk,
        )
        return {'email_sent': False, 'recipient': user.email, 'status': 'failed'}

    logger.info(
        'Onboarding email queued user_id=%s tenant_id=%s password_link=%s verify_link=%s',
        user.pk,
        getattr(tenant, 'pk', None),
        bool(set_password_url),
        bool(verify_url),
    )
    return {'email_sent': True, 'recipient': user.email, 'status': 'queued'}
