"""Paginación con techo explícito.

``LimitOffsetPagination`` de DRF no aplica ``MAX_PAGE_SIZE``: sin un ``max_limit``
un cliente puede pedir ``?limit=1000000`` y forzar la serialización de toda una
tabla. Este subclass toma el techo de ``REST_FRAMEWORK['MAX_PAGE_SIZE']`` para
que la configuración deje de ser engañosa (BE-15).
"""
from django.conf import settings
from rest_framework.pagination import LimitOffsetPagination

DEFAULT_MAX_PAGE_SIZE = 200


class BoundedLimitOffsetPagination(LimitOffsetPagination):
    @property
    def max_limit(self):
        """Techo configurado; 200 por compatibilidad con el valor histórico."""
        rest_framework_settings = getattr(settings, 'REST_FRAMEWORK', {}) or {}
        return rest_framework_settings.get('MAX_PAGE_SIZE', DEFAULT_MAX_PAGE_SIZE)
