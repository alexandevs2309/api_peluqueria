import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone

@pytest.mark.django_db
def test_sales_report(authenticated_user):
    user, client = authenticated_user
    client.force_authenticate(user=user)
    response = client.get(reverse("sales-report"))
    assert response.status_code == status.HTTP_200_OK
    assert "date" in response.data
    assert "total_sales" in response.data
    assert "transaction_count" in response.data

@pytest.mark.django_db
def test_appointments_report(authenticated_user):
    user, client = authenticated_user
    client.force_authenticate(user=user)
    response = client.get(reverse("appointments-report"))
    assert response.status_code == status.HTTP_200_OK
    assert "date" in response.data
    assert "total_appointments" in response.data

@pytest.mark.django_db
def test_employee_performance_report(authenticated_user):
    user, client = authenticated_user
    client.force_authenticate(user=user)
    response = client.get(reverse("employee-performance-report"))
    assert response.status_code == status.HTTP_200_OK
