import pytest
from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.urls import reverse
from apps.auth_api.factories import UserFactory
from apps.roles_api.models import Role, UserRole
from apps.employees_api.models import Employee, WorkSchedule
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription

User = get_user_model()

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
def test_create_employee_success(admin_client, stylist_user):
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


@pytest.fixture
def tenant_for_schedules(db):
    plan, _ = SubscriptionPlan.objects.get_or_create(
        name='basic',
        defaults={
            'description': 'Plan base test',
            'price': 0,
            'duration_month': 1,
            'max_employees': 50,
            'max_users': 50,
            'is_active': True,
            'features': {}
        }
    )
    owner = User.objects.create_superuser(
        email='owner.schedules@example.com',
        password='testpassword123',
        full_name='Owner Schedules'
    )
    return Tenant.objects.create(
        name=f"Tenant Schedules {owner.id}",
        subdomain=f"tenant-schedules-{owner.id}",
        owner=owner,
        is_active=True,
        subscription_plan=plan,
        subscription_status='active',
    )


@pytest.fixture
def manager_user(tenant_for_schedules):
    manager = User.objects.create_user(
        email='manager.schedules@example.com',
        password='testpassword123',
        full_name='Manager Schedules',
        tenant=tenant_for_schedules,
        is_email_verified=True
    )
    role, _ = Role.objects.get_or_create(
        name='Manager',
        defaults={'scope': 'TENANT', 'description': 'Manager test role'}
    )
    perms = Permission.objects.filter(
        content_type__app_label='employees_api',
        codename__in=['view_employee', 'change_employee']
    )
    role.permissions.add(*perms)
    UserRole.objects.get_or_create(user=manager, role=role, tenant=tenant_for_schedules)
    Employee.objects.get_or_create(
        user=manager,
        defaults={'tenant': tenant_for_schedules, 'specialty': 'Manager'}
    )
    return manager


@pytest.fixture
def manager_client(manager_user):
    client = APIClient()
    refresh = RefreshToken.for_user(manager_user)
    refresh['tenant_id'] = manager_user.tenant_id
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


@pytest.fixture
def team_employee(tenant_for_schedules):
    worker_user = User.objects.create_user(
        email='worker.schedules@example.com',
        password='testpassword123',
        full_name='Worker Schedules',
        tenant=tenant_for_schedules,
        is_email_verified=True
    )
    return Employee.objects.create(
        user=worker_user,
        tenant=tenant_for_schedules,
        specialty='Stylist'
    )


@pytest.mark.django_db
def test_manager_can_create_schedule_for_team_employee(manager_client, team_employee):
    payload = {
        'employee': team_employee.id,
        'day_of_week': 'monday',
        'start_time': '09:00:00',
        'end_time': '17:00:00'
    }
    response = manager_client.post(reverse('work_schedule-list'), payload, format='json')
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_manager_can_update_schedule_for_team_employee(manager_client, team_employee):
    schedule = WorkSchedule.objects.create(
        employee=team_employee,
        day_of_week='tuesday',
        start_time='09:00:00',
        end_time='17:00:00'
    )
    payload = {
        'employee': team_employee.id,
        'day_of_week': 'tuesday',
        'start_time': '10:00:00',
        'end_time': '18:00:00'
    }
    response = manager_client.put(
        reverse('work_schedule-detail', kwargs={'pk': schedule.id}),
        payload,
        format='json'
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_manager_cannot_delete_schedule_sensitive_action(manager_client, team_employee):
    schedule = WorkSchedule.objects.create(
        employee=team_employee,
        day_of_week='wednesday',
        start_time='09:00:00',
        end_time='17:00:00'
    )
    response = manager_client.delete(
        reverse('work_schedule-detail', kwargs={'pk': schedule.id})
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
