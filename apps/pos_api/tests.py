import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status 
from rest_framework.test import APIClient
from apps.inventory_api.models import Product, StockMovement
from apps.appointments_api.models import Appointment
from apps.clients_api.models import Client
from apps.pos_api.models import CashRegister, Sale

@pytest.mark.django_db
def test_sale_with_product_discounts_stock(authenticated_user):
    user, client = authenticated_user
    product = Product.objects.create(name="Shampoo", sku="SH001", price=100, stock=10, min_stock=2)

    data = {
        "client": None,
        "total": 100.0,
        "discount": 0.0,
        "paid": 100.0,
        "payment_method": "cash",
        "details": [
            {"content_type": "product", "object_id": product.id, "name": product.name, "quantity": 1, "price": 100.0}
        ],
        "payments": [
            {"method": "cash", "amount": 100.0}
        ]
    }

    client.force_authenticate(user=user)
    response = client.post(reverse("sale-list"), data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    product.refresh_from_db()
    assert product.stock == 9
    assert StockMovement.objects.filter(product=product, quantity=-1).exists()

@pytest.mark.django_db
def test_sale_linked_to_appointment(authenticated_user, client_factory, service_factory, stylist, stylist_role):
    user, client = authenticated_user
    client_obj = client_factory.create()
    service = service_factory()
    stylist_user, employee = stylist

    # Crear cita programada
    appointment = Appointment.objects.create(
        client=client_obj,
        stylist=stylist_user,
        role=stylist_role,
        service=service,
        date_time=timezone.now() + timezone.timedelta(days=1),
        status="scheduled"
    )

    data = {
        "client": client_obj.id,
        "total": 100.0,
        "discount": 20.0,
        "paid": 100.0,
        "payment_method": "cash",
        "details": [
            {"content_type": "service", "object_id": service.id, "name": service.name, "quantity": 1, "price": 120.0}
        ],
        "payments": [
            {"method": "cash", "amount": 100.0}
        ],
        "appointment": appointment.id
    }

    client.force_authenticate(user=user)
    response = client.post(reverse("sale-list"), data, format="json")

    assert response.status_code == status.HTTP_201_CREATED , f"Error: {response.data}"

    appointment.refresh_from_db()
    assert appointment.status == "completed"
    assert appointment.sale_id == response.data["id"]

@pytest.mark.django_db
def test_daily_summary_endpoint(authenticated_user):
    user, client = authenticated_user

    # Crear una venta para hoy
    Sale.objects.create(
        client=None,
        user=user,
        date_time=timezone.now(),
        total=150,
        discount=0,
        paid=150,
        payment_method="cash"
    )

    client.force_authenticate(user=user)
    response = client.get(reverse("daily-summary"))

    assert response.status_code == 200
    assert response.data["sales_count"] == 1
    assert response.data["total"] == 150

@pytest.mark.django_db
def test_low_stock_alerts(authenticated_user):
    user, client = authenticated_user
    p1 = Product.objects.create(name="Pomada", sku="P001", price=50, stock=1, min_stock=2)
    p2 = Product.objects.create(name="Cera", sku="P002", price=60, stock=5, min_stock=2)

    client.force_authenticate(user=user)
    response = client.get(reverse("low-stock-alerts"))

    assert response.status_code == 200
    product_names = [p["name"] for p in response.data]
    assert "Pomada" in product_names
    assert "Cera" not in product_names


@pytest.mark.django_db
def test_close_cash_register(authenticated_user):
    user, client = authenticated_user
    register = CashRegister.objects.create(user=user, is_open=True, opened_at=timezone.now())

    client.force_authenticate(user=user)
    url = reverse("cash-register-close", kwargs={"pk": register.id})
    data = {"final_cash": 100.0}
    response = client.post(url, data, format="json")

    assert response.status_code == status.HTTP_200_OK
    register.refresh_from_db()
    assert not register.is_open
    assert register.final_cash == 100.0

@pytest.mark.django_db
def test_close_already_closed_cash_register(authenticated_user):
    user, client = authenticated_user
    register = CashRegister.objects.create(user=user, is_open=False, opened_at=timezone.now())

    client.force_authenticate(user=user)
    url = reverse("cash-register-close", kwargs={"pk": register.id})
    data = {"final_cash": 100.0}
    response = client.post(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "Caja ya está cerrada."


@pytest.mark.django_db
def test_close_cash_register(authenticated_user):
    user, client = authenticated_user
    register = CashRegister.objects.create(user=user, is_open=True, opened_at=timezone.now())

    client.force_authenticate(user=user)
    url = reverse("cash-register-close", kwargs={"pk": register.id})
    data = {"final_cash": 100.0}
    response = client.post(url, data, format="json")

    assert response.status_code == status.HTTP_200_OK
    register.refresh_from_db()
    assert not register.is_open
    assert register.final_cash == 100.0

@pytest.mark.django_db
def test_close_already_closed_cash_register(authenticated_user):
    user, client = authenticated_user
    register = CashRegister.objects.create(
        user=user, 
        is_open=False, 
        opened_at=timezone.now())

    client.force_authenticate(user=user)
    url = reverse("cash-register-close", kwargs={"pk": register.id})
    data = {"final_cash": 100.0}
    response = client.post(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "Caja ya está cerrada."


@pytest.mark.django_db
def test_close_cash_register_view_invalid_final_cash(authenticated_user):
    user, client = authenticated_user
    register = CashRegister.objects.create(user=user, is_open=True ,opened_at=timezone.now)

    client.force_authenticate(user=user)
    url = reverse("cash-register-close", kwargs={"pk": register.id})
    data = {"final_cash": "not_a_number"}  # Invalid final cash value
    response = client.post(url, data, format="json")
    assert response.status_code == 400
    assert "final_cash" in str(response.data).lower()
