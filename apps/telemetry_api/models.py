import logging

from django.conf import settings
from django.db import models

logger = logging.getLogger('api.telemetry')


class FrontendErrorEvent(models.Model):
    """Evento de error reportado por el frontend (ErrorLoggerService)."""

    timestamp = models.DateTimeField(auto_now_add=True)
    severity = models.CharField(max_length=16, default='ERROR')
    type = models.CharField(max_length=32, default='EVENT')
    code = models.CharField(max_length=64, blank=True, default='')
    message = models.CharField(max_length=500, blank=True, default='')
    url = models.CharField(max_length=500, blank=True, default='')
    module = models.CharField(max_length=128, blank=True, default='')
    user_id = models.CharField(max_length=64, blank=True, null=True)
    user_email = models.EmailField(blank=True, null=True)
    tenant_id = models.CharField(max_length=64, blank=True, null=True)
    trace_id = models.CharField(max_length=64, blank=True, null=True)
    incident_id = models.CharField(max_length=32, blank=True, null=True)
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    origin = models.CharField(max_length=32, blank=True, default='')
    browser = models.CharField(max_length=32, blank=True, default='')
    raw = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = 'telemetry_api'
        db_table = 'telemetry_frontend_error_event'
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['severity']),
            models.Index(fields=['module']),
        ]

    def __str__(self):
        return f'{self.timestamp:%Y-%m-%d %H:%M} {self.type}/{self.code} {self.message[:60]}'

    @classmethod
    def ingest_batch(cls, events):
        created = 0
        for ev in events or []:
            if not isinstance(ev, dict):
                continue
            try:
                cls.objects.create(
                    severity=str(ev.get('severity') or 'ERROR')[:16],
                    type=str(ev.get('type') or 'EVENT')[:32],
                    code=str(ev.get('code') or '')[:64],
                    message=str(ev.get('message') or '')[:500],
                    url=str(ev.get('url') or '')[:500],
                    module=str(ev.get('module') or '')[:128],
                    user_id=(str(ev['user_id'])[:64] if ev.get('user_id') else None),
                    user_email=(str(ev['user_email'])[:254] if ev.get('user_email') else None),
                    tenant_id=(str(ev['tenant_id'])[:64] if ev.get('tenant_id') else None),
                    trace_id=(str(ev['trace_id'])[:64] if ev.get('trace_id') else None),
                    incident_id=(str(ev['incident_id'])[:32] if ev.get('incident_id') else None),
                    http_status=(int(ev['http_status']) if ev.get('http_status') else None),
                    origin=str(ev.get('origin') or '')[:32],
                    browser=str(ev.get('browser') or '')[:32],
                    raw=ev,
                )
                created += 1
            except Exception as exc:  # nunca romper por un evento mal formado
                logger.warning('FrontendErrorEvent.ingest_batch skip: %s', exc)
        return created

    @classmethod
    def forward_to_sentry(cls, events):
        """Reenvía solo los críticos a Sentry con tags de correlación."""
        if not getattr(settings, 'SENTRY_DSN', None):
            return
        try:
            import sentry_sdk
        except ImportError:
            return
        for ev in events or []:
            if isinstance(ev, dict) and str(ev.get('severity')) in ('CRITICAL', 'ERROR'):
                sentry_sdk.capture_message(
                    f"[frontend] {ev.get('type', 'EVENT')}/{ev.get('code') or 'no-code'} {str(ev.get('message'))[:200]}",
                    level=str(ev.get('severity') or 'error').lower(),
                    extras={
                        'module': ev.get('module'),
                        'url': ev.get('url'),
                        'incident_id': ev.get('incident_id'),
                        'trace_id': ev.get('trace_id'),
                        'user_id': ev.get('user_id'),
                        'tenant_id': ev.get('tenant_id'),
                        'browser': ev.get('browser'),
                    },
                )
