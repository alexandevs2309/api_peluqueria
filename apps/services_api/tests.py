import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .models import Service
from .serializers import ServiceSerializer
from apps.roles_api.models import Role, UserRole
from apps.auth_api.factories import UserFactory
from apps.tenants_api.models import Tenant
from faker import Faker

faker = Faker('es_ES')

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_tenant():
    return Tenant.objects.create(
        name=faker.company(),
        subdomain=faker.slug()
    )

@pytest.fixture
def authenticated_user(api_client, test_tenant):
    user = UserFactory(
        email=faker.email(),
        password='testpass123',
        tenant=test_tenant
    )
    from apps.roles_api.default_permissions import ROLE_PERMISSIONS
    role, _ = Role.objects.get_or_create(name='Estilista', defaults={'scope': 'TENANT'})
    perms = Permission.objects.filter(content_type__app_label='services_api')
    role.permissions.add(*perms)
    UserRole.objects.get_or_create(user=user, role=role, tenant=test_tenant)
    api_client.force_authenticate(user=user)
    return user, api_client

@pytest.fixture
def admin_user(api_client, test_tenant):
    user = UserFactory(
        email=faker.email(),
        password='testpass123',
        is_superuser=True,
        tenant=test_tenant
    )
    api_client.force_authenticate(user=user)
    return user, api_client

@pytest.fixture
def service_factory(test_tenant):
    class ServiceFactory:
        @staticmethod
        def create(**kwargs):
            defaults = {
                'name': faker.word(),
                'description': faker.text(),
                'price': float(faker.pydecimal(left_digits=4, right_digits=2, positive=True)),
                'is_active': True,
                'tenant': test_tenant,
            }
            defaults.update(kwargs)
            service = Service.objects.create(**defaults)
            return service
    return ServiceFactory()

@pytest.mark.django_db
def test_create_service(admin_user, service_factory):
    user, client = admin_user
    data = {
        'name': 'Corte Clásico',
        'description': 'Corte de cabello tradicional',
        'price': 1500.00,
        'is_active': True,
    }
    response = client.post(reverse('service-list'), data, format='json')
    assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
    assert Service.objects.count() == 1
    service = Service.objects.first()
    assert service.name == 'Corte Clásico'
    assert service.price == 1500.00
    assert service.allowed_roles.count() == 0

@pytest.mark.django_db
def test_create_service_with_roles(admin_user, service_factory):
    user, client = admin_user
    role, _ = Role.objects.get_or_create(name='Estilista', defaults={'scope': 'TENANT'})
    data = {
        'name': 'Corte Premium',
        'description': 'Corte de alta calidad',
        'price': 2500.00,
        'is_active': True,
        'allowed_roles': [role.id],
    }
    response = client.post(reverse('service-list'), data, format='json')
    assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
    assert Service.objects.count() == 1
    service = Service.objects.first()
    assert service.name == 'Corte Premium'
    assert service.allowed_roles.count() == 1
    assert service.allowed_roles.first().name == 'Estilista'

@pytest.mark.django_db
def test_list_services(authenticated_user, service_factory):
    user, client = authenticated_user
    service_factory.create(name='Corte Moderno', is_active=True)
    service_factory.create(name='Afeitado', is_active=False)
    response = client.get(reverse('service-list'))
    assert response.status_code == status.HTTP_200_OK
    results = response.data['results'] if isinstance(response.data, dict) else response.data
    assert len(results) == 2, f"Esperado 2, obtenido {len(results)}: {results}"

@pytest.mark.django_db
def test_update_service(admin_user, service_factory):
    user, client = admin_user
    service = service_factory.create(name='Corte Básico')
    data = {
        'name': 'Corte Actualizado',
        'description': 'Corte mejorado',
        'price': 2000.00,
        'is_active': True,
    }
    response = client.put(reverse('service-detail', kwargs={'pk': service.id}), data, format='json')
    assert response.status_code == status.HTTP_200_OK, f"Error: {response.data}"
    service.refresh_from_db()
    assert service.name == 'Corte Actualizado'
    assert service.price == 2000.00

@pytest.mark.django_db
def test_partial_update_service(admin_user, service_factory):
    user, client = admin_user
    service = service_factory.create(name='Corte Básico', price=1000.00)
    data = {'price': 1200.00}
    response = client.patch(reverse('service-detail', kwargs={'pk': service.id}), data, format='json')
    assert response.status_code == status.HTTP_200_OK, f"Error: {response.data}"
    service.refresh_from_db()
    assert service.name == 'Corte Básico'
    assert service.price == 1200.00

@pytest.mark.django_db
def test_delete_service(admin_user, service_factory):
    user, client = admin_user
    service = service_factory.create(name='Corte Básico')
    response = client.delete(reverse('service-detail', kwargs={'pk': service.id}))
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert Service.objects.count() == 0

@pytest.mark.django_db
def test_create_service_invalid_data(admin_user):
    user, client = admin_user
    data = {
        'name': 'Corte Inválido',
        'description': 'Corte con precio negativo',
        'price': -100.00,
        'is_active': True,
    }
    response = client.post(reverse('service-list'), data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    details = response.data.get('details', response.data) if isinstance(response.data, dict) else response.data
    assert 'price' in details
    assert Service.objects.count() == 0

@pytest.mark.django_db
def test_create_service_duplicate_name(admin_user, service_factory):
    user, client = admin_user
    service_factory.create(name='Corte Duplicado')
    data = {
        'name': 'Corte Duplicado',
        'description': 'Intento de duplicado',
        'price': 1500.00,
        'is_active': True,
    }
    response = client.post(reverse('service-list'), data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    details = response.data.get('details', response.data) if isinstance(response.data, dict) else response.data
    assert 'name' in details
