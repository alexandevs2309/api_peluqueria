import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from apps.inventory_api.models import Product, StockMovement
from apps.appointments_api.models import Appointment
from apps.pos_api.models import CashRegister, Sale

@pytest.mark.django_db
def test_sale_with_product_discounts_stock(authenticated_user):
    user, client = authenticated_user
    user.is_superuser = True
    user.save()
    CashRegister.objects.create(user=user, tenant=user.tenant, is_open=True, opened_at=timezone.now(), initial_cash=0)
    product = Product.objects.create(name="Shampoo", sku="SH001", price=100, stock=10, min_stock=2, tenant=user.tenant)

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
def test_sale_linked_to_appointment(authenticated_user, client, client_factory, service_factory, stylist, stylist_role):
    user, api_client = authenticated_user
    user.is_superuser = True
    user.save()
    CashRegister.objects.create(user=user, tenant=user.tenant, is_open=True, opened_at=timezone.now(), initial_cash=0)
    client_obj = client_factory.create()
    service = service_factory()
    stylist_user, employee = stylist

    # Crear cita programada
    appointment = Appointment.objects.create(
        tenant=user.tenant,
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

    api_client.force_authenticate(user=user)
    response = api_client.post(reverse("sale-list"), data, format="json")

    assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"

    appointment.refresh_from_db()
    assert appointment.status == "completed"
    assert appointment.sale_id == response.data["id"]

@pytest.mark.django_db
def test_daily_summary_endpoint(authenticated_user):
    user, client = authenticated_user
    user.is_superuser = True
    user.save()

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
    user.is_superuser = True
    user.save()
    p1 = Product.objects.create(name="Pomada", sku="P001", price=50, stock=1, min_stock=2, tenant=user.tenant)
    p2 = Product.objects.create(name="Cera", sku="P002", price=60, stock=5, min_stock=2, tenant=user.tenant)

    client.force_authenticate(user=user)
    response = client.get(reverse("low-stock-alerts"))

    assert response.status_code == 200
    product_names = [p["name"] for p in response.data["products"]]
    assert "Pomada" in product_names
    assert "Cera" not in product_names

@pytest.mark.django_db
def test_close_cash_register(authenticated_user):
    user, client = authenticated_user
    user.is_superuser = True
    user.save()
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
    user.is_superuser = True
    user.save()
    register = CashRegister.objects.create(user=user, is_open=False, opened_at=timezone.now())

    client.force_authenticate(user=user)
    url = reverse("cash-register-close", kwargs={"pk": register.id})
    data = {"final_cash": 100.0}
    response = client.post(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["detail"] == "Caja ya está cerrada."

@pytest.mark.django_db
def test_close_cash_register_view_invalid_final_cash(authenticated_user):
    user, client = authenticated_user
    user.is_superuser = True
    user.save()
    try:
        register = CashRegister.objects.create(user=user, is_open=True, opened_at=timezone.now())
        
        client.force_authenticate(user=user)
        url = reverse("cash-register-close", kwargs={"pk": register.id})
        data = {"final_cash": "not_a_number"}  # Invalid final cash value
        response = client.post(url, data, format="json")
        assert response.status_code == 400
        assert "final_cash" in str(response.data).lower()
    except Exception as e:
        pytest.fail(f"Test failed with error: {e}")


@pytest.mark.django_db
def test_sale_on_other_user_cash_register_rejected():
    """
    Usuario A intenta vender explícitamente en la caja de usuario B
    usando el campo cash_register. Debe rechazar con 400.
    """
    from apps.auth_api.factories import UserFactory
    from apps.services_api.models import Service

    # Crear dos usuarios en el mismo tenant
    user_a = UserFactory(email="user_a@test.com")
    user_a.is_superuser = True
    user_a.save()
    user_b = UserFactory(email="user_b@test.com", tenant=user_a.tenant)

    # user_b abre su propia caja
    register_b = CashRegister.objects.create(
        user=user_b, tenant=user_a.tenant, is_open=True,
        opened_at=timezone.now(), initial_cash=0,
    )

    # user_a crea un servicio para tener algo que vender
    service = Service.objects.create(
        name="Corte Test", price=200, is_active=True, tenant=user_a.tenant,
    )

    # Autenticar como user_a e intentar vender en la caja de user_b
    api_client = APIClient()
    api_client.force_authenticate(user=user_a)

    data = {
        "client": None,
        "total": 200.0,
        "discount": 0.0,
        "paid": 200.0,
        "payment_method": "cash",
        "cash_register": register_b.id,
        "details": [
            {"content_type": "service", "object_id": service.id, "name": service.name, "quantity": 1, "price": 200.0}
        ],
        "payments": [
            {"method": "cash", "amount": 200.0}
        ],
    }

    response = api_client.post(reverse("sale-list"), data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST, f"Expected 400, got {response.status_code}: {response.data}"
    # Verificar que el error menciona la caja
    error_str = str(response.data)
    assert "caja" in error_str.lower() or "cash_register" in error_str.lower(), f"Expected cash register error, got: {error_str}"


@pytest.mark.django_db
def test_sale_on_own_cash_register_accepted():
    """
    Usuario A vende en su propia caja usando el campo cash_register.
    Debe aceptar con 201.
    """
    from apps.auth_api.factories import UserFactory
    from apps.services_api.models import Service

    user_a = UserFactory(email="user_a_own@test.com")
    user_a.is_superuser = True
    user_a.save()
    service = Service.objects.create(
        name="Corte Own", price=150, is_active=True, tenant=user_a.tenant,
    )

    # user_a abre su propia caja
    register_a = CashRegister.objects.create(
        user=user_a, tenant=user_a.tenant, is_open=True,
        opened_at=timezone.now(), initial_cash=50,
    )

    api_client = APIClient()
    api_client.force_authenticate(user=user_a)

    data = {
        "client": None,
        "total": 150.0,
        "discount": 0.0,
        "paid": 150.0,
        "payment_method": "cash",
        "cash_register": register_a.id,
        "details": [
            {"content_type": "service", "object_id": service.id, "name": service.name, "quantity": 1, "price": 150.0}
        ],
        "payments": [
            {"method": "cash", "amount": 150.0}
        ],
    }

    response = api_client.post(reverse("sale-list"), data, format="json")

    assert response.status_code == status.HTTP_201_CREATED, f"Expected 201, got {response.status_code}: {response.data}"


@pytest.mark.django_db
def test_sale_on_closed_cash_register_rejected():
    """
    Usuario envía una caja cerrada. Debe rechazar con 400.
    """
    from apps.auth_api.factories import UserFactory
    from apps.services_api.models import Service

    user = UserFactory(email="user_closed@test.com")
    user.is_superuser = True
    user.save()
    service = Service.objects.create(
        name="Corte Closed", price=100, is_active=True, tenant=user.tenant,
    )

    closed_register = CashRegister.objects.create(
        user=user, tenant=user.tenant, is_open=False,
        opened_at=timezone.now(), closed_at=timezone.now(),
        initial_cash=0, final_cash=100,
    )

    api_client = APIClient()
    api_client.force_authenticate(user=user)

    data = {
        "client": None,
        "total": 100.0,
        "discount": 0.0,
        "paid": 100.0,
        "payment_method": "cash",
        "cash_register": closed_register.id,
        "details": [
            {"content_type": "service", "object_id": service.id, "name": service.name, "quantity": 1, "price": 100.0}
        ],
        "payments": [
            {"method": "cash", "amount": 100.0}
        ],
    }

    response = api_client.post(reverse("sale-list"), data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST, f"Expected 400, got {response.status_code}: {response.data}"
    error_str = str(response.data)
    assert "abierta" in error_str.lower() or "open" in error_str.lower() or "cash_register" in error_str.lower(), f"Expected open register error, got: {error_str}"
