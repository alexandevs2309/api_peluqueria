# conftest.py
import pytest
from django.conf import settings

@pytest.fixture(scope='session', autouse=True)
def configure_settings():
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
