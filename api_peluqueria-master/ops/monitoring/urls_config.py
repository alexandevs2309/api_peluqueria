# Agregar a backend/urls.py

from ops.monitoring.health_views import health_check, metrics

urlpatterns = [
    # ... tus URLs existentes
    path('health/', health_check, name='health_check'),
    path('metrics/', metrics, name='metrics'),
]