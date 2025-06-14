import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.services_api.models import Service, StylistService
from apps.clients_api.models import Client
from django.contrib.auth import get_user_model
from .models import Appointment
from faker import Faker
from datetime import datetime, timedelta, timezone as dt_timezone
from django.utils import timezone
from apps.roles_api.models import Role, UserRole

faker = Faker('es_ES')
User = get_user_model()

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
def client_factory():
    class ClientFactory:
        @staticmethod
        def create(**kwargs):
            user = User.objects.create_user(
                email=faker.email(),
                password='testpass123',
            )
            defaults = {
                'user': user,
                'full_name': faker.name(),
                'email': faker.email(),
                'phone': faker.phone_number(),
                'created_by': user,
            }
            defaults.update(kwargs)
            return Client.objects.create(**defaults)
    return ClientFactory()

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
            return Service.objects.create(**defaults)
    return ServiceFactory()

@pytest.fixture
def stylist_role():
    return Role.objects.create(name='stylist')

@pytest.fixture
def stylist(stylist_role):
    user = User.objects.create_user(
        email=faker.email(),
        password='testpass123',
        is_staff=True
    )
    UserRole.objects.create(user=user, role=stylist_role)
    return user  # Devolver User en lugar de Role

@pytest.mark.django_db
def test_create_appointment_with_service(authenticated_user, client_factory, service_factory, stylist, stylist_role):
    user, client = authenticated_user
    client_obj = client_factory.create()
    future_date_time = timezone.now() + timedelta(days=1)
    service = service_factory.create(name='Corte Básico')
    # Crear StylistService para pasar la validación
    StylistService.objects.create(stylist=stylist, service=service, duration=timedelta(minutes=30))
    data = {
        'client': client_obj.id,
        'stylist': stylist.id,
        'service': service.id,
        'role': stylist_role.id,
        'date_time': future_date_time 
    }
    response = client.post(reverse('appointment-list'), data, format='json')
    assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
    appointment = Appointment.objects.first()
    assert appointment.service == service
    assert appointment.date_time.year == 2025

@pytest.mark.django_db
def test_create_appointment_without_service(authenticated_user, client_factory, stylist, stylist_role):
    user, client = authenticated_user
    client_obj = client_factory.create()
    future_date_time = timezone.now() + timedelta(days=1)
    data = {
        'client': client_obj.id,
        'stylist': stylist.id,
        'role': stylist_role.id,
        'date_time': future_date_time,
    }
    response = client.post(reverse('appointment-list'), data, format='json')
    assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
    assert Appointment.objects.count() == 1
    appointment = Appointment.objects.first()
    assert appointment.service is None

@pytest.mark.django_db
def test_list_appointments(api_client, client_factory, stylist, service_factory, stylist_role):
    # Use the stylist's credentials for authentication since they should see the appointments
    api_client.force_authenticate(user=stylist)
    client_obj = client_factory.create()
    service = service_factory.create(name='Corte Básico')
    StylistService.objects.create(stylist=stylist, service=service, duration=timedelta(minutes=30))  # Añadido
    Appointment.objects.create(
        client=client_obj,
        stylist=stylist,
        service=service,
        role=stylist_role,
        date_time=datetime(2025, 6, 12, 10, 0, tzinfo=dt_timezone.utc)
    )
    Appointment.objects.create(
        client=client_obj,
        stylist=stylist,
        service=None,
        role=stylist_role,
        date_time=datetime(2025, 6, 12, 11, 0, tzinfo=dt_timezone.utc)
    )
    response = api_client.get(reverse('appointment-list'))
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['results']) == 2
