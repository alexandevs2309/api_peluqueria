from decimal import Decimal
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.utils import timezone
from apps.auth_api.models import User
from apps.billing_api.serializers import InvoiceSerializer
from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription
from apps.billing_api.models import Invoice, PaymentAttempt


@pytest.fixture
def user_subscription(user):
    plan = SubscriptionPlan.objects.create(
        name="Básico",
        price=10.00,
        duration_month=1,
        max_employees=5,
        features={"billing_enabled": True}
    )
    return UserSubscription.objects.create(
        user=user,
        plan=plan,
        start_date=timezone.now() - timezone.timedelta(days=1),
        end_date=timezone.now() + timezone.timedelta(days=30),
        is_active=True,
        auto_renew=True
    )

@pytest.fixture
def invoice(user):
    return Invoice.objects.create(
        user=user,
        amount=Decimal("100.00"),
        due_date=timezone.now() + timezone.timedelta(days=7),
        is_paid=False,
    )


@pytest.fixture
def user_with_active_subscription(db):
    user = User.objects.create_user(email="billinguser@test.com", password="pass1234")
    plan = SubscriptionPlan.objects.create(
        name="Premium",
        price=100,
        duration_month=1,
        max_employees=10,
    )
    UserSubscription.objects.create(
        user=user,
        plan=plan,
        start_date=timezone.now(),
        end_date=timezone.now() + timezone.timedelta(days=30),
        is_active=True
    )
    return user


@pytest.fixture
def auth_client(user_with_active_subscription):
    client = APIClient()
    client.force_authenticate(user=user_with_active_subscription)
    return client


@pytest.mark.django_db
def test_create_invoice(auth_client, user_with_active_subscription):
    payload = {
        "amount": "150.00",
        "description": "Test invoice",
        "due_date": (timezone.now() + timezone.timedelta(days=7)).isoformat(),
    }
    response = auth_client.post(reverse("invoice-list"), payload, format="json")
    if response.status_code != status.HTTP_201_CREATED:
        print("Error response data:", response.data)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["amount"] == "150.00"
    assert response.data["description"] == "Test invoice"


@pytest.mark.django_db
def test_list_own_invoices(auth_client):
    response = auth_client.get(reverse("invoice-list"))
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.data, dict) or isinstance(response.data, list)
    

@pytest.mark.django_db
def test_pay_invoice(auth_client, user_with_active_subscription):
    invoice = Invoice.objects.create(
        user=user_with_active_subscription,
        amount=100.0,
        description="To pay",
        due_date=timezone.now() + timezone.timedelta(days=5)
    )

    url = reverse("invoice-pay", args=[invoice.pk])
    response = auth_client.post(url)
    assert response.status_code == status.HTTP_200_OK
    assert response.data["detail"] in ["Pago procesado con éxito.", "Pago exitoso."]
    invoice.refresh_from_db()
    assert invoice.is_paid is True


@pytest.mark.django_db
def test_cannot_pay_twice(auth_client, user_with_active_subscription):
    invoice = Invoice.objects.create(
        user=user_with_active_subscription,
        amount=80.0,
        is_paid=True,
        description="Paid already",
        due_date=timezone.now() + timezone.timedelta(days=3)
    )
    url = reverse("invoice-pay", args=[invoice.pk])
    response = auth_client.post(url)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "ya fue pagada" in response.data["detail"]


@pytest.mark.django_db
def test_user_cannot_see_others_invoices(auth_client):
    other_user = User.objects.create_user(email="other@test.com", password="otherpass")
    invoice = Invoice.objects.create(
        user=other_user,
        amount=60.0,
        description="Other user invoice",
        due_date=timezone.now() + timezone.timedelta(days=5)
    )
    url = reverse("invoice-detail", args=[invoice.pk])
    response = auth_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_list_payment_attempts(auth_client, user_with_active_subscription):
    invoice = Invoice.objects.create(
        user=user_with_active_subscription,
        amount=90.0,
        due_date=timezone.now(),
    )
    PaymentAttempt.objects.filter(invoice=invoice).delete()
    PaymentAttempt.objects.create(invoice=invoice, success=True, message="Success")
    PaymentAttempt.objects.create(invoice=invoice, success=False, message="Failed")

    response = auth_client.get(reverse("payment-attempt-list"))
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['results']) == 2
    assert any([a["success"] for a in response.data['results']])



@pytest.mark.django_db
def test_invoice_payment_success(api_client, user, user_subscription):
    invoice = Invoice.objects.create(user=user, subscription=user_subscription, amount=100, due_date=timezone.now() + timezone.timedelta(days=5))
    url = reverse('invoice-pay', args=[invoice.id])
    api_client.force_authenticate(user)
    response = api_client.post(url)
    assert response.status_code == 200
    assert response.data["detail"] == "Pago exitoso."
    invoice.refresh_from_db()
    assert invoice.is_paid is True


@pytest.mark.django_db
def test_invoice_already_paid(api_client, user, user_subscription):
    invoice = Invoice.objects.create(user=user, subscription=user_subscription, amount=100, is_paid=True , due_date=timezone.now() + timezone.timedelta(days=5))
    url = reverse('invoice-pay', args=[invoice.id])
    api_client.force_authenticate(user)
    response = api_client.post(url)
    assert response.status_code == 400
    assert "ya fue pagada" in response.data["detail"]


@pytest.mark.django_db
def test_invoice_visibility_for_non_owner(api_client, user, another_user, user_subscription):
    invoice = Invoice.objects.create(user=another_user, subscription=user_subscription, amount=100 ,due_date=timezone.now() + timezone.timedelta(days=5))
    api_client.force_authenticate(user)
    url = reverse('invoice-detail', args=[invoice.id])
    response = api_client.get(url)
    assert response.status_code in [403, 404]  # Dependiendo de cómo Django maneje el queryset vacío


@pytest.mark.django_db
def test_payment_attempt_list(api_client, user, user_subscription):
    invoice = Invoice.objects.create(user=user, subscription=user_subscription, amount=100,due_date=timezone.now() + timezone.timedelta(days=5))
    PaymentAttempt.objects.create(invoice=invoice, success=True, message="test")

    api_client.force_authenticate(user)
    url = reverse('payment-attempt-list')
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data['results'][0]["message"] == "test"


def test_invoice_serializer_output():
    invoice = Invoice(amount=123.45, is_paid=False)
    serializer = InvoiceSerializer(instance=invoice)
    data = serializer.data
    assert "amount" in data
    assert data["is_paid"] is False


@pytest.mark.django_db
def test_invoice_creation_uses_active_subscription(auth_client, user_with_active_subscription):
    """
    Cubre perform_create en InvoiceViewSet.
    """
    url = reverse("invoice-list")
    payload = {
        "amount": "200.00",
        "description": "Factura automática",
        "due_date": (timezone.now() + timezone.timedelta(days=5)).isoformat()
    }

    response = auth_client.post(url, payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    invoice_id = response.data["id"]
    invoice = Invoice.objects.get(id=invoice_id)

    assert invoice.subscription is not None
    assert invoice.subscription.user == invoice.user


@pytest.mark.django_db
def test_superuser_can_list_all_invoices():
    superuser = User.objects.create_superuser(email="admin@admin.com", password="adminpass")
    client = APIClient()
    client.force_authenticate(superuser)

    Invoice.objects.create(user=superuser, amount=10, due_date=timezone.now())

    response = client.get(reverse("invoice-list"))
    assert response.status_code == 200
    assert response.data["count"] >= 1


@pytest.mark.django_db
def test_invoice_creation_missing_fields(auth_client):
    response = auth_client.post(reverse("invoice-list"), {"description": "Incomplete"}, format="json")
    assert response.status_code == 400
    assert "amount" in response.data
    assert "due_date" in response.data
