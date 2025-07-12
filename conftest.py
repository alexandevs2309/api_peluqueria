import pytest
from django.conf import settings
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from faker import Faker
from apps.clients_api.models import Client
from apps.services_api.models import Service
from apps.roles_api.models import Role
from django.utils import timezone
from datetime import timedelta

faker = Faker()
User = get_user_model()


@pytest.fixture
def client_factory():
    """Crea y retorna un Client para pruebas."""
    class ClientFactory:
        @staticmethod
        def create(**kwargs):
            user = User.objects.create_user(email=faker.email(), password='testpass123')
            defaults = {
                'user': user,
                'full_name': faker.name(),
                'email': faker.email(),
                'phone': faker.phone_number(),
                'created_by': user,
            }
            defaults.update(kwargs)
            return Client.objects.create(**defaults)

    return ClientFactory

@pytest.fixture(autouse=True)
def set_urlconf():
    """Se asegura de que todas las pruebas usen el urls.py de backend."""
    settings.ROOT_URLCONF = 'backend.urls'


@pytest.fixture
def api_client():
    """Retorna una instancia de APIClient para pruebas."""
    return APIClient()


@pytest.fixture
def authenticated_user(api_client):
    """Crea y autentica un usuario para pruebas."""
    user = User.objects.create_user(
        email=faker.email(),
        password='testpass123'
    )
    api_client.force_authenticate(user=user)
    return user, api_client


@pytest.fixture
def service_factory():
    """Crea y retorna un servicio para pruebas."""
    def create_service(**kwargs):
        defaults = {
            'name': faker.word(),
            'price': 100.0,
            'description': faker.text(),
            'is_active': True,
        }
        defaults.update(kwargs)
        service = Service.objects.create(**defaults)
        return service
    return create_service


@pytest.fixture
def stylist():
    """Crea y retorna un usuario estilista y su empleado asociado."""
    user = User.objects.create_user(
        email=faker.email(),
        password='testpass123',
        is_staff=True
    )
    return user, None  # Assuming employee object is not needed or created elsewhere


@pytest.fixture
def stylist_role():
    """Crea y retorna un rol para estilista."""
    role, created = Role.objects.get_or_create(name='Stylist')
    return role
