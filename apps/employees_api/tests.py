import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from django.urls import reverse
from apps.auth_api.factories import UserFactory
from apps.roles_api.models import Role, UserRole
from apps.employees_api.models import Employee, WorkSchedule
from apps.services_api.models import Service
from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription
from apps.subscriptions_api.tests import user

@pytest.fixture
def admin_client(db):
    user = UserFactory(is_email_verified=True, is_superuser=True , is_staff=True)
    client = APIClient()
    client.force_authenticate(user=user)
    return client

@pytest.fixture
def stylist_user(db):
    user = UserFactory(is_email_verified=True)
    stylist_role, _ = Role.objects.get_or_create(name='Stylist')
    UserRole.objects.get_or_create(user=user, role=stylist_role)
    return user

@pytest.fixture
def normal_client(db):
    user = UserFactory(is_email_verified=True)
    client = APIClient()
    client.force_authenticate(user=user)
    return client

@pytest.mark.django_db
def test_create_employee_success(admin_client, stylist_user, user):
    # Crear plan con 5 empleados permitidos
    plan = SubscriptionPlan.objects.create(
        name="Pro",
        price=0,
        duration_month=1,
        max_employees=5
    )
    # Suscripción activa para el stylist_user
    UserSubscription.objects.create(
        user=stylist_user,
        plan=plan,
        start_date=timezone.now() - timezone.timedelta(days=1),
        end_date=timezone.now() + timezone.timedelta(days=29),
        is_active=True,
        auto_renew=True
    )

    payload = {
        'user_id': stylist_user.id,
        'specialty': 'Hair Stylist',
        'phone': '1234567890',
        'hire_date': '2025-06-01',
        'is_active': True
    }
    response = admin_client.post(reverse('employee-list'), payload, format='json')
    print("Status:", response.status_code)
    print("Errors:", response.data)  # 👈 Esto es clave
    assert response.status_code == status.HTTP_201_CREATED

@pytest.mark.django_db
def test_create_employee_missing_data(admin_client):
    response = admin_client.post(reverse('employee-list'), {}, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST 

@pytest.mark.django_db
def test_delete_nonexistent_employee(admin_client):
    response = admin_client.delete(reverse('employee-detail', kwargs={'pk': 9999}))
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
def test_list_employees_denied_to_non_admin(normal_client):
    response = normal_client.get(reverse('employee-list'))
    assert response.status_code in [403, 401]

@pytest.mark.django_db
def test_create_schedule_denied_for_stylist(stylist_user):
    client = APIClient()
    client.force_authenticate(user=stylist_user)
    employee = Employee.objects.create(user=stylist_user, specialty='Stylist')
    payload = {
        'employee': employee.id,
        'day_of_week': 'monday',
        'start_time': '09:00:00',
        'end_time': '17:00:00'
    }
    response = client.post(reverse('work_schedule-list'), payload, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_stylist_cannot_create_other_employee(stylist_user):
    client = APIClient()
    client.force_authenticate(user=stylist_user)
    other_user = UserFactory(is_email_verified=True)
    payload = {
        'user_email': other_user.id,
        'specialty': 'Nail Technician',
        'phone': '0987654321',
        'hire_date': '2025-06-01',
        'is_active': True
    }
    response = client.post(reverse('employee-list'), payload, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.django_db
def test_update_employee_denied_for_non_admin(normal_client):
    employee = Employee.objects.create(user=UserFactory(), specialty="Stylist")
    response = normal_client.put(reverse("employee-detail", args=[employee.id]), {"specialty": "Updated"})
    assert response.status_code in [403, 401]

@pytest.mark.django_db
def test_permission_denied_if_inactive():
    user = UserFactory(is_email_verified=True, is_active=False)
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("employee-list"))
    assert response.status_code in [403, 401]

@pytest.mark.django_db
def test_delete_employee_permission_denied_other_roles():
    user = UserFactory(is_email_verified=True)
    employee = Employee.objects.create(user=UserFactory(), specialty="Stylist")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.delete(reverse("employee-detail", args=[employee.id]))
    assert response.status_code in [403, 401]
