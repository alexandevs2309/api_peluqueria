import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from apps.pos_api.models import Coupon, CashRegister, Sale
from decimal import Decimal

@pytest.mark.django_db
def test_coupon_validation_success_percentage(authenticated_user):
    user, api_client = authenticated_user
    user.is_superuser = True
    user.save()

    now = timezone.now()
    coupon = Coupon.objects.create(
        tenant=user.tenant,
        code="PERCENT50",
        description="50% Off",
        type="percentage",
        value=Decimal("50.00"),
        min_purchase_amount=Decimal("100.00"),
        start_date=now - timezone.timedelta(days=1),
        end_date=now + timezone.timedelta(days=1),
        is_active=True,
        max_uses=10,
        current_uses=0
    )

    api_client.force_authenticate(user=user)
    data = {
        "code": "PERCENT50",
        "cart_total": 200.00
    }
    url = reverse("coupon-validate")
    response = api_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["coupon_id"] == coupon.id
    assert response.data["code"] == "PERCENT50"
    assert response.data["type"] == "percentage"
    # 50% of 200 is 100
    assert float(response.data["discount"]) == 100.00


@pytest.mark.django_db
def test_coupon_validation_success_fixed(authenticated_user):
    user, api_client = authenticated_user
    user.is_superuser = True
    user.save()

    now = timezone.now()
    coupon = Coupon.objects.create(
        tenant=user.tenant,
        code="FIXED20",
        description="20 DOP Off",
        type="fixed",
        value=Decimal("20.00"),
        min_purchase_amount=Decimal("50.00"),
        start_date=now - timezone.timedelta(days=1),
        end_date=now + timezone.timedelta(days=1),
        is_active=True,
        max_uses=10,
        current_uses=0
    )

    api_client.force_authenticate(user=user)
    data = {
        "code": "FIXED20",
        "cart_total": 80.00
    }
    url = reverse("coupon-validate")
    response = api_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["coupon_id"] == coupon.id
    assert response.data["type"] == "fixed"
    assert float(response.data["discount"]) == 20.00


@pytest.mark.django_db
def test_coupon_validation_inactive(authenticated_user):
    user, api_client = authenticated_user
    user.is_superuser = True
    user.save()

    now = timezone.now()
    coupon = Coupon.objects.create(
        tenant=user.tenant,
        code="INACTIVE",
        type="fixed",
        value=Decimal("10.00"),
        start_date=now - timezone.timedelta(days=1),
        end_date=now + timezone.timedelta(days=1),
        is_active=False
    )

    api_client.force_authenticate(user=user)
    data = {
        "code": "INACTIVE",
        "cart_total": 50.00
    }
    url = reverse("coupon-validate")
    response = api_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "no está activo" in response.data["error"]


@pytest.mark.django_db
def test_coupon_validation_expired(authenticated_user):
    user, api_client = authenticated_user
    user.is_superuser = True
    user.save()

    now = timezone.now()
    coupon = Coupon.objects.create(
        tenant=user.tenant,
        code="EXPIRED",
        type="fixed",
        value=Decimal("10.00"),
        start_date=now - timezone.timedelta(days=5),
        end_date=now - timezone.timedelta(days=1),
        is_active=True
    )

    api_client.force_authenticate(user=user)
    data = {
        "code": "EXPIRED",
        "cart_total": 50.00
    }
    url = reverse("coupon-validate")
    response = api_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "expirado" in response.data["error"]


@pytest.mark.django_db
def test_coupon_validation_not_started(authenticated_user):
    user, api_client = authenticated_user
    user.is_superuser = True
    user.save()

    now = timezone.now()
    coupon = Coupon.objects.create(
        tenant=user.tenant,
        code="FUTURE",
        type="fixed",
        value=Decimal("10.00"),
        start_date=now + timezone.timedelta(days=1),
        end_date=now + timezone.timedelta(days=5),
        is_active=True
    )

    api_client.force_authenticate(user=user)
    data = {
        "code": "FUTURE",
        "cart_total": 50.00
    }
    url = reverse("coupon-validate")
    response = api_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "vigencia" in response.data["error"]


@pytest.mark.django_db
def test_coupon_validation_max_uses(authenticated_user):
    user, api_client = authenticated_user
    user.is_superuser = True
    user.save()

    now = timezone.now()
    coupon = Coupon.objects.create(
        tenant=user.tenant,
        code="MAXED",
        type="fixed",
        value=Decimal("10.00"),
        start_date=now - timezone.timedelta(days=1),
        end_date=now + timezone.timedelta(days=1),
        is_active=True,
        max_uses=3,
        current_uses=3
    )

    api_client.force_authenticate(user=user)
    data = {
        "code": "MAXED",
        "cart_total": 50.00
    }
    url = reverse("coupon-validate")
    response = api_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "límite" in response.data["error"]


@pytest.mark.django_db
def test_coupon_validation_min_purchase(authenticated_user):
    user, api_client = authenticated_user
    user.is_superuser = True
    user.save()

    now = timezone.now()
    coupon = Coupon.objects.create(
        tenant=user.tenant,
        code="MIN100",
        type="fixed",
        value=Decimal("10.00"),
        min_purchase_amount=Decimal("100.00"),
        start_date=now - timezone.timedelta(days=1),
        end_date=now + timezone.timedelta(days=1),
        is_active=True
    )

    api_client.force_authenticate(user=user)
    data = {
        "code": "MIN100",
        "cart_total": 50.00
    }
    url = reverse("coupon-validate")
    response = api_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Compra mínima requerida" in response.data["error"]


from apps.tenants_api.models import Tenant

@pytest.mark.django_db
def test_coupon_validation_tenant_isolation(authenticated_user):
    user, api_client = authenticated_user
    user.is_superuser = True
    user.save()

    other_tenant = Tenant.objects.create(name="Barberia B", subdomain="barberiab")
    now = timezone.now()
    coupon = Coupon.objects.create(
        tenant=other_tenant,
        code="OTHERTENANT",
        type="fixed",
        value=Decimal("10.00"),
        start_date=now - timezone.timedelta(days=1),
        end_date=now + timezone.timedelta(days=1),
        is_active=True
    )

    api_client.force_authenticate(user=user)
    data = {
        "code": "OTHERTENANT",
        "cart_total": 50.00
    }
    url = reverse("coupon-validate")
    response = api_client.post(url, data, format="json")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "no existe" in response.data["error"]


from apps.inventory_api.models import Product

@pytest.mark.django_db
def test_sale_creation_with_coupon(authenticated_user):
    user, api_client = authenticated_user
    user.is_superuser = True
    user.save()

    CashRegister.objects.create(user=user, tenant=user.tenant, is_open=True, opened_at=timezone.now(), initial_cash=0)
    product = Product.objects.create(name="Shampoo", sku="SH001", price=100.00, stock=10, min_stock=2, tenant=user.tenant)

    now = timezone.now()
    coupon = Coupon.objects.create(
        tenant=user.tenant,
        code="SALE50",
        type="percentage",
        value=Decimal("50.00"),
        min_purchase_amount=Decimal("10.00"),
        start_date=now - timezone.timedelta(days=1),
        end_date=now + timezone.timedelta(days=1),
        is_active=True,
        max_uses=10,
        current_uses=0
    )

    data = {
        "client": None,
        "total": 100.0,
        "discount": 50.0,  # 50% discount
        "paid": 50.0,
        "payment_method": "cash",
        "details": [
            {"content_type": "product", "object_id": product.id, "name": product.name, "quantity": 1, "price": 100.0}
        ],
        "payments": [
            {"method": "cash", "amount": 50.0}
        ],
        "coupon_id": coupon.id,
        "discount_reason": "Descuento de cupón de verano SALE50"
    }

    api_client.force_authenticate(user=user)
    response = api_client.post(reverse("sale-list"), data, format="json")

    assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
    
    # Reload coupon to check uses
    coupon.refresh_from_db()
    assert coupon.current_uses == 1

    # Check that Sale is linked to the coupon
    sale = Sale.objects.get(id=response.data["id"])
    assert sale.coupon == coupon
    assert sale.coupon_code == "SALE50"
    assert float(sale.total) == 50.0
    assert float(sale.discount) == 50.0
