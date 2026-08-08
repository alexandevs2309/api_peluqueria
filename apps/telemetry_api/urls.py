from django.urls import path

from apps.telemetry_api.views import errors_ingest

urlpatterns = [
    path('errors/', errors_ingest, name='telemetry-errors-ingest'),
]
