"""Credenciales de IA por tenant para el Asistente IA (ADR-001).

La clave del proveedor se guarda cifrada con la misma ``FERNET_KEY`` que
protege las credenciales de pago. En producción no hay fallback a texto plano:
``backend/settings.py`` ya valida que la clave Fernet exista al arrancar.
"""
from django.conf import settings
from django.core import signing
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantModel


class TenantAiCredential(TenantModel):
    """Configuración BYOK / plan incluido de un negocio.

    Una fila por tenant (garantizado por la constraint única). El tenant llega
    del JWT vía TenantMiddleware; nunca se acepta desde el payload del chat.
    """

    MODE_BYOK = 'byok'
    MODE_INCLUDED = 'included'
    MODE_CHOICES = (
        (MODE_BYOK, 'Clave propia (BYOK)'),
        (MODE_INCLUDED, 'IA incluida (cupo mensual)'),
    )

    PROVIDER_GEMINI = 'gemini'
    PROVIDER_OPENAI = 'openai'
    PROVIDER_DEEPSEEK = 'deepseek'
    PROVIDER_CHOICES = (
        (PROVIDER_GEMINI, 'Google Gemini'),
        (PROVIDER_OPENAI, 'OpenAI'),
        (PROVIDER_DEEPSEEK, 'DeepSeek'),
    )

    FERNET_PREFIX = 'gAAAAA'
    SIGNING_SALT = 'tenant_ai_credential'

    mode = models.CharField(_('Modo'), max_length=16, choices=MODE_CHOICES, default=MODE_BYOK)
    provider = models.CharField(
        _('Proveedor'), max_length=16, choices=PROVIDER_CHOICES, default=PROVIDER_GEMINI
    )
    encrypted_api_key = models.TextField(_('Clave cifrada'), blank=True)
    key_hint = models.CharField(_('Pista de la clave'), max_length=8, blank=True)
    monthly_request_limit = models.PositiveIntegerField(
        _('Límite mensual de peticiones (modo incluido)'), default=100
    )
    requests_this_month = models.PositiveIntegerField(_('Peticiones del mes'), default=0)
    period_month = models.CharField(_('Período (YYYY-MM)'), max_length=7, blank=True)
    is_active = models.BooleanField(_('Activa'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Credencial de IA del negocio')
        verbose_name_plural = _('Credenciales de IA de los negocios')
        constraints = [
            models.UniqueConstraint(
                fields=['tenant'], name='unique_ai_credential_per_tenant'
            )
        ]

    def __str__(self):
        return f'{self.tenant_id} - {self.provider} ({self.mode})'

    # --- cifrado ---------------------------------------------------------
    @staticmethod
    def _fernet():
        from cryptography.fernet import Fernet

        key = getattr(settings, 'FERNET_KEY', None)
        if not key:
            if not getattr(settings, 'DEBUG', True):
                raise RuntimeError(
                    'FERNET_KEY no configurada: no se pueden guardar credenciales de IA.'
                )
            return None
        return Fernet(key.encode() if isinstance(key, str) else key)

    @staticmethod
    def mask(value: str) -> str:
        if not value:
            return ''
        return f'••••{value[-4:]}' if len(value) > 4 else '••••'

    @classmethod
    def encrypt_key(cls, value: str) -> str:
        if not value:
            return ''
        fernet = cls._fernet()
        if fernet is not None:
            return fernet.encrypt(value.encode('utf-8')).decode('utf-8')
        # Solo en DEBUG (o tests): integridad con firma, nunca texto plano.
        return signing.dumps(value, salt=cls.SIGNING_SALT, compress=True)

    @classmethod
    def decrypt_key(cls, value: str) -> str:
        if not value:
            return ''
        if value.startswith(cls.FERNET_PREFIX):
            fernet = cls._fernet()
            if fernet is None:
                return ''
            try:
                return fernet.decrypt(value.encode('utf-8')).decode('utf-8')
            except Exception:
                return ''
        try:
            return signing.loads(value, salt=cls.SIGNING_SALT)
        except (signing.BadSignature, signing.SignatureExpired):
            return ''

    def set_api_key(self, value: str) -> None:
        value = (value or '').strip()
        self.encrypted_api_key = self.encrypt_key(value) if value else ''
        self.key_hint = self.mask(value)

    def get_api_key(self) -> str:
        return self.decrypt_key(self.encrypted_api_key)

    # --- cupo mensual (modo incluido) ------------------------------------
    def _current_period(self) -> str:
        return timezone.now().strftime('%Y-%m')

    def refresh_period(self) -> None:
        period = self._current_period()
        if self.period_month != period:
            self.period_month = period
            self.requests_this_month = 0

    def has_quota(self) -> bool:
        return self.monthly_request_limit <= 0 or self.requests_this_month < self.monthly_request_limit

    def consume_request(self) -> bool:
        """Reserva una petición del cupo. Devuelve False si no hay cupo."""
        from django.db.models import F

        self.refresh_period()
        if not self.has_quota():
            return False
        updated = type(self).objects.filter(pk=self.pk, is_active=True).update(
            requests_this_month=F('requests_this_month') + 1,
            period_month=self.period_month,
        )
        if updated:
            self.requests_this_month += 1
        return bool(updated)
