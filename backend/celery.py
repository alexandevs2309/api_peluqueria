from __future__ import absolute_import, unicode_literals
import os
import logging
from celery import Celery

logger = logging.getLogger(__name__)

# Establece el módulo de configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

app = Celery('backend')

# Cargar configuración desde Django (prefijadas con CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodescubre tareas de todos los apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    logger.debug(f'Request: {self.request!r}')
