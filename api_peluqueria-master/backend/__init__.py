from __future__ import absolute_import, unicode_literals

# Asegúrate de importar la app de Celery al iniciar Django
from .celery import app as celery

__all__ = ('celery',)
