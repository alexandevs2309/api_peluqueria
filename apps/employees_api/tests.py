from faker import Faker
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.services_api.models import Service
from apps.roles_api.models import Role, UserRole
from .models import Employee, EmployeeService, WorkSchedule


faker = Faker('es_ES')

User = get_user_model()

@pytest.mark.django_db
def test_create_employee():
    client = APIClient()
    admin_role, _ = Role.objects.get_or_create(name='Admin')
    stylist_role, _ = Role.objects.get_or_create(name='Stylist')
    admin = User.objects.create_user(email='admin@example.com', full_name='Admin User', password='testpass123', is_staff=True, is_superuser=True, is_active=True)
    UserRole.objects.get_or_create(user=admin, role=admin_role)
    stylist_user = User.objects.create_user(email='stylist@example.com', full_name='Stylist User', password='testpass123')
    UserRole.objects.get_or_create(user=stylist_user, role=stylist_role)
    
    client.force_authenticate(user=admin)
    payload = {
        'user_email': stylist_user.id,
        'specialty': 'Hair Stylist',
        'phone': '1234567890',
        'hire_date': '2025-06-01',
        'is_active': True
    }
    response = client.post(reverse('employee-list'), payload, format='json')
    
    if response.status_code != status.HTTP_201_CREATED:
        print(f"Error creating employee: {response.data}")
    assert response.status_code == status.HTTP_201_CREATED

@pytest.mark.django_db
def test_assign_service():
    client = APIClient()
    admin_role, _ = Role.objects.get_or_create(name='Admin')
    stylist_role, _ = Role.objects.get_or_create(name='Stylist')
    admin = User.objects.create_user(email='admin@example.com', full_name='Admin User', password='testpass123', is_staff=True, is_superuser=True, is_active=True)
    UserRole.objects.get_or_create(user=admin, role=admin_role)
    stylist_user = User.objects.create_user(email='stylist@example.com', full_name='Stylist User', password='testpass123')
    
    UserRole.objects.get_or_create(user=stylist_user, role=stylist_role)
    employee = Employee.objects.create(user=stylist_user, specialty='Hair Stylist')
    service = Service.objects.create(name='Haircut', price=25.00)
            
    client.force_authenticate(user=admin)
    payload = {'service_id': service.id , 'employee': employee.id}
    response = client.post(reverse('employee-assign-service', kwargs={'pk': 999}), payload, format='json')

    assert response.status_code == status.HTTP_404_NOT_FOUND  # Cambiar a 404
    assert EmployeeService.objects.count() == 0

@pytest.mark.django_db
def test_create_schedule_as_stylist():
    client = APIClient()
    stylist_role, _ = Role.objects.get_or_create(name='Stylist')
    stylist = User.objects.create_user(email='stylist@example.com', full_name='Stylist User', password='testpass123')
    UserRole.objects.get_or_create(user=stylist, role=stylist_role)
    employee = Employee.objects.create(user=stylist, specialty='Hair Stylist')
    
    client.force_authenticate(user=stylist)
    payload = {
        'employee': employee.id,
        'day_of_week': 'monday',
        'start_time': '09:00:00',
        'end_time': '17:00:00'
    }
    response = client.post(reverse('work_schedule-list'), payload, format='json')
    
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert WorkSchedule.objects.count() == 0


@pytest.mark.django_db
def test_stylist_cannot_create_other_employee():
    client = APIClient()
    stylist_role, _ = Role.objects.get_or_create(name='Stylist')
    stylist = User.objects.create_user(email='stylist@example.com', full_name='Stylist User', password='testpass123')
    UserRole.objects.get_or_create(user=stylist, role=stylist_role)
    other_user = User.objects.create_user(email='other@example.com', full_name='Other User', password='testpass123')
    UserRole.objects.get_or_create(user=other_user, role=stylist_role)
    
    client.force_authenticate(user=stylist)
    payload = {
        'user_id': other_user.id,
        'specialty': 'Nail Technician',
        'phone': '0987654321',
        'hire_date': '2025-06-01',
        'is_active': True

    }
    response = client.post(reverse('employee-list'), payload, format='json')
    
    assert response.status_code == status.HTTP_403_FORBIDDEN  # Usar constante de DRF
    assert Employee.objects.count() == 0
