from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Establece el módulo de configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')  # ⬅️ reemplaza 'backend' si es necesario

app = Celery('backend')  # ⬅️ usa el mismo nombre del módulo raíz

# Cargar configuración desde Django (prefijadas con CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodescubre tareas de todos los apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
