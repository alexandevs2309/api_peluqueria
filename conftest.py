import os
import django
from django.conf import settings

if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.test_settings')
    django.setup()

import pytest

collect_ignore = ["test_full_flow.py", "test_perm.py", "test_real_http.py"]

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from faker import Faker
from apps.auth_api.factories import UserFactory as _UserFactory
from apps.clients_api.models import Client
from apps.services_api.models import Service
from apps.roles_api.models import Role
from django.utils import timezone
from datetime import timedelta

from apps.subscriptions_api.models import UserSubscription

faker = Faker()
User = get_user_model()


@pytest.fixture
def client_factory():
    """Crea y retorna un Client para pruebas."""
    class ClientFactory:
        @staticmethod
        def create(**kwargs):
            user = _UserFactory()
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
    return APIClient()


@pytest.fixture
def authenticated_user(api_client):
    """Crea y autentica un usuario para pruebas."""
    user = _UserFactory()
    api_client.force_authenticate(user=user)
    return user, api_client


@pytest.fixture
def role_with_all_permissions(db):
    """Crea un Role con todos los permisos de billing/payments."""
    from django.contrib.auth.models import Permission
    from apps.roles_api.models import Role

    role, _ = Role.objects.get_or_create(name='TestFullAccess')
    perms = Permission.objects.filter(
        content_type__app_label__in=['billing_api', 'payments_api'],
        codename__in=[
            'view_invoice', 'add_invoice', 'change_invoice', 'delete_invoice',
            'view_paymentattempt', 'add_paymentattempt',
            'change_paymentattempt', 'delete_paymentattempt',
            'view_payment', 'add_payment', 'change_payment', 'delete_payment',
        ]
    )
    role.permissions.add(*perms)
    return role


@pytest.fixture
def authorized_user(api_client, role_with_all_permissions):
    """Crea y autentica un usuario con todos los permisos de billing/payments."""
    from apps.roles_api.models import UserRole

    user = _UserFactory()
    UserRole.objects.create(user=user, role=role_with_all_permissions, tenant=user.tenant)
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
    user = _UserFactory(is_staff=True)
    return user, None  # Assuming employee object is not needed or created elsewhere


@pytest.fixture
def stylist_role():
    """Crea y retorna un rol para estilista."""
    role, created = Role.objects.get_or_create(name='Stylist')
    return role


@pytest.fixture
def user(db):
    return _UserFactory(email="test@example.com")

@pytest.fixture
def another_user(db):
    return _UserFactory(email="other@example.com")

@pytest.fixture
def user_subscription(user):
    return UserSubscription.objects.create(user=user, is_active=True)


@pytest.fixture(autouse=True)
def ensure_test_owner(db):
    if not User.objects.exists():
        User.objects.create_user(
            email='test-tenant-owner@example.com',
            password='pass',
            is_superuser=True,
        )
    return None
