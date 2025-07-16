import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .models import Service
from .serializers import ServiceSerializer
from apps.roles_api.models import Role
from faker import Faker

faker = Faker('es_ES')

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def authenticated_user(api_client, django_user_model):
    user = django_user_model.objects.create_user(
        email=faker.email(),
        password='testpass123'
    )
    api_client.force_authenticate(user=user)
    return user, api_client

@pytest.fixture
def admin_user(api_client, django_user_model):
    user = django_user_model.objects.create_superuser(
        email=faker.email(),
        password='testpass123'
    )
    api_client.force_authenticate(user=user)
    return user, api_client

@pytest.fixture
def service_factory():
    class ServiceFactory:
        @staticmethod
        def create(**kwargs):
            defaults = {
                'name': faker.word(),
                'description': faker.text(),
                'price': float(faker.pydecimal(left_digits=4, right_digits=2, positive=True)),
                'is_active': True,
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
    role = Role.objects.create(name='Estilista')
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
    assert len(response.data['results']) == 1, f"Esperado 1, obtenido {len(response.data['results'])}: {response.data['results']}"
    if len(response.data['results']) > 0:
        assert response.data['results'][0]['name'] == 'Corte Moderno'

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
    assert 'price' in response.data
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
    assert 'name' in response.data