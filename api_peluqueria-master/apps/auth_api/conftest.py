# apps/roles_api/tests.py o un conftest.py para crear roles base

import pytest
from apps.roles_api.models import Role # Importa Role

# Este fixture se ejecutará una vez por sesión de prueba
@pytest.fixture(scope="session", autouse=True)
def setup_roles_for_tests(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # Crea los roles base que usarán tus tests si no existen
        Role.objects.get_or_create(name='Admin', defaults={'description': 'Administrador del sistema'})
        Role.objects.get_or_create(name='Client', defaults={'description': 'Cliente regular'})
        # Asegúrate de que los nombres coincidan exactamente con lo que usas en el código
        # por ejemplo, 'Admin' con 'A' mayúscula