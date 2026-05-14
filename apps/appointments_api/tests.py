import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.services_api.models import Service, StylistService
from apps.clients_api.models import Client
from django.contrib.auth import get_user_model

from apps.employees_api.models import WorkSchedule, Employee
from .models import Appointment
from faker import Faker
from datetime import datetime, timedelta, timezone as dt_timezone
from django.utils import timezone
from apps.roles_api.models import Role, UserRole
from apps.auth_api.factories import UserFactory
from apps.tenants_api.models import Tenant

faker = Faker('es_ES')
User = get_user_model()


@pytest.fixture
def test_tenant():
    return Tenant.objects.create(
        name=faker.company(),
        subdomain=faker.slug()
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_user(api_client, test_tenant):
    user = UserFactory(
        email=faker.email(),
        password='testpass123',
        tenant=test_tenant
    )
    api_client.force_authenticate(user=user)
    return user, api_client


@pytest.fixture
def client_factory(test_tenant):
    class ClientFactory:
        @staticmethod
        def create(**kwargs):
            user = UserFactory(tenant=test_tenant)
            defaults = {
                'user': user,
                'tenant': test_tenant,
                'full_name': faker.name(),
                'email': faker.email(),
                'phone': faker.phone_number(),
                'created_by': user,
            }
            defaults.update(kwargs)
            return Client.objects.create(**defaults)
    return ClientFactory()


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
            return Service.objects.create(**defaults)
    return ServiceFactory()


@pytest.fixture
def stylist_role():
    return Role.objects.create(name='stylist')


@pytest.fixture
def stylist(stylist_role, test_tenant):
    user = UserFactory(
        email=faker.email(),
        password='testpass123',
        tenant=test_tenant,
    )
    UserRole.objects.create(user=user, role=stylist_role, tenant=test_tenant)
    employee = Employee.objects.create(user=user, specialty='Corte de cabello', tenant=test_tenant)
    return user, employee


@pytest.mark.django_db
def test_create_appointment_with_service(authenticated_user, client_factory, service_factory, stylist, stylist_role):
    user, client = authenticated_user
    client_obj = client_factory.create()
    service = service_factory.create(name='Corte Básico')
    stylist_user, employee = stylist

    from datetime import time
    appointment_datetime = timezone.localtime(timezone.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    naive_future_datetime = appointment_datetime.replace(tzinfo=None)
    day_name = appointment_datetime.strftime('%A').lower()
    start_time = time(9, 0)
    end_time = time(18, 0)

    StylistService.objects.create(stylist=stylist_user, service=service, duration=timedelta(minutes=30))

    WorkSchedule.objects.create(
        employee=employee,
        day_of_week=day_name,
        start_time=start_time,
        end_time=end_time
    )

    data = {
        'client': client_obj.id,
        'stylist': stylist_user.id,
        'service': service.id,
        'role': stylist_role.id,
        'date_time': naive_future_datetime.isoformat()
    }

    response = client.post(reverse('appointment-list'), data, format='json')
    assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
    appointment = Appointment.objects.first()
    assert appointment.service == service


@pytest.mark.django_db
def test_create_appointment_without_service(authenticated_user, client_factory, stylist, stylist_role):
    user, client = authenticated_user
    client_obj = client_factory.create()
    stylist_user, employee = stylist

    from datetime import time
    appointment_datetime = timezone.localtime(timezone.now() + timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0)
    naive_future_datetime = appointment_datetime.replace(tzinfo=None)
    day_name = appointment_datetime.strftime('%A').lower()
    start_time = time(9, 0)
    end_time = time(18, 0)

    WorkSchedule.objects.create(
        employee=employee,
        day_of_week=day_name,
        start_time=start_time,
        end_time=end_time
    )

    data = {
        'client': client_obj.id,
        'stylist': stylist_user.id,
        'role': stylist_role.id,
        'date_time': naive_future_datetime.isoformat()
    }

    response = client.post(reverse('appointment-list'), data, format='json')
    assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
    assert Appointment.objects.count() == 1
    appointment = Appointment.objects.first()
    assert appointment.service is None


@pytest.mark.django_db
def test_list_appointments(api_client, client_factory, stylist, service_factory, stylist_role, test_tenant):
    stylist_user, employee = stylist
    api_client.force_authenticate(user=stylist_user)
    client_obj = client_factory.create()
    service = service_factory.create(name='Corte Básico')
    StylistService.objects.create(stylist=stylist_user, service=service, duration=timedelta(minutes=30))

    appointment_date = datetime(2025, 6, 12, tzinfo=dt_timezone.utc)
    WorkSchedule.objects.create(
        employee=employee,
        day_of_week=appointment_date.strftime('%A').lower(),
        start_time=datetime(2025, 6, 12, 9, 0).time(),
        end_time=datetime(2025, 6, 12, 12, 0).time()
    )
    Appointment.objects.create(
        client=client_obj,
        stylist=stylist_user,
        service=service,
        role=stylist_role,
        tenant=test_tenant,
        date_time=datetime(2025, 6, 12, 10, 0, tzinfo=dt_timezone.utc)
    )
    Appointment.objects.create(
        client=client_obj,
        stylist=stylist_user,
        service=None,
        role=stylist_role,
        tenant=test_tenant,
        date_time=datetime(2025, 6, 12, 11, 0, tzinfo=dt_timezone.utc)
    )
    response = api_client.get(reverse('appointment-list'))
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['results']) == 2


@pytest.mark.django_db
def test_create_appointment_invalid_service():
    user = UserFactory(is_email_verified=True)
    client = APIClient()
    client.force_authenticate(user=user)
    data = {
        "date_time": "2030-01-01T10:00:00Z",
        "service": 9999
    }
    response = client.post(reverse("appointment-list"), data, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_create_appointment_stylist_without_employee(client_factory, service_factory, stylist_role, test_tenant):
    user = UserFactory(tenant=test_tenant, email='stylist@nomodel.com', password='pass')
    UserRole.objects.create(user=user, role=stylist_role, tenant=test_tenant)
    client_obj = client_factory.create()
    service = service_factory.create()

    appointment_datetime = timezone.localtime(timezone.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    naive_dt = appointment_datetime.replace(tzinfo=None)

    data = {
        'client': client_obj.id,
        'stylist': user.id,
        'role': stylist_role.id,
        'service': service.id,
        'date_time': naive_dt.isoformat()
    }

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(reverse("appointment-list"), data, format="json")
    assert response.status_code == 400
    assert "no tiene un perfil de empleado" in str(response.data)


@pytest.mark.django_db
def test_create_appointment_outside_schedule(client_factory, service_factory, stylist, stylist_role):
    stylist_user, employee = stylist
    client_obj = client_factory.create()
    service = service_factory.create()
    appointment_datetime = timezone.localtime(timezone.now() + timedelta(days=1)).replace(hour=22, minute=0, second=0, microsecond=0)
    naive_dt = appointment_datetime.replace(tzinfo=None)
    day_name = appointment_datetime.strftime('%A').lower()

    WorkSchedule.objects.create(employee=employee, day_of_week=day_name, start_time=datetime(2025,1,1,9,0).time(), end_time=datetime(2025,1,1,18,0).time())
    StylistService.objects.create(stylist=stylist_user, service=service, duration=timedelta(minutes=30))

    data = {
        'client': client_obj.id,
        'stylist': stylist_user.id,
        'role': stylist_role.id,
        'service': service.id,
        'date_time': naive_dt.isoformat()
    }

    client = APIClient()
    client.force_authenticate(user=stylist_user)
    response = client.post(reverse("appointment-list"), data, format="json")
    assert response.status_code == 400
    assert "no está disponible en este horario" in str(response.data)


@pytest.mark.django_db
def test_create_appointment_service_not_offered(client_factory, service_factory, stylist, stylist_role):
    stylist_user, employee = stylist
    client_obj = client_factory.create()
    service = service_factory.create()

    appointment_datetime = timezone.localtime(timezone.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    naive_dt = appointment_datetime.replace(tzinfo=None)
    day_name = appointment_datetime.strftime('%A').lower()
    WorkSchedule.objects.create(employee=employee, day_of_week=day_name, start_time=datetime(2025,1,1,9,0).time(), end_time=datetime(2025,1,1,18,0).time())

    data = {
        'client': client_obj.id,
        'stylist': stylist_user.id,
        'role': stylist_role.id,
        'service': service.id,
        'date_time': naive_dt.isoformat()
    }

    client = APIClient()
    client.force_authenticate(user=stylist_user)
    response = client.post(reverse("appointment-list"), data, format="json")
    assert response.status_code == 400
    assert "no ofrece este servicio" in str(response.data)
