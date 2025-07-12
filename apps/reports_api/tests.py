import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from apps.pos_api.models import Sale


@pytest.fixture
def admin_user(db, django_user_model):
    user = django_user_model.objects.create_superuser(
        email="admin@example.com",
        password="password123",
        is_staff=True,
        is_active=True,
    )
    return user



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


@pytest.mark.django_db
def test_report_export_invalid_format(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    url = reverse("export-reports") + "?format=invalid"
    response = client.get(url)

    assert response.status_code in [400, 404]  # Bad request or not found
    
# @pytest.mark.django_db
# def test_report_export_csv(admin_user):
#     client = APIClient()
#     client.force_authenticate(user=admin_user)
#     url = reverse("export-reports") + "?format=csv"
#     print(f"Testing URL: {url}")

#     Sale.objects.create(
#         user=admin_user,
#         date_time=timezone.now(),
#         total=100.00,
#         paid=100.00,
#         payment_method='cash'
#     )

#     response = client.get(url, follow=True)  # Follow redirects

#     assert response.status_code == status.HTTP_200_OK
#     assert response["Content-Type"] in ["text/csv", "application/csv"]
#     content = response.content.decode("utf-8")
#     assert "ID" in content
#     assert "Total" in content
#     assert "Método de pago" in content
