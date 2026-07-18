import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.pos_api.models import NCFSequence, Sale, CashRegister
from apps.tenants_api.models import Tenant
from django.contrib.auth import get_user_model
import datetime

User = get_user_model()

@pytest.fixture
def other_tenant(db):
    return Tenant.objects.create(name="Other Barbershop", subdomain="other")

@pytest.fixture
def other_user(db, other_tenant):
    user = User.objects.create_user(
        email="other@barber.com",
        password="password123",
        role="CLIENT_ADMIN",
        tenant=other_tenant
    )
    return user

@pytest.mark.django_db
def test_ncf_sequence_model_validation():
    # Test valid model constraints
    tenant = Tenant.objects.create(name="Test Tenant", subdomain="test")
    
    # Expiration check
    seq = NCFSequence.objects.create(
        tenant=tenant,
        type="02",
        prefix="B",
        start_sequence=1,
        end_sequence=10,
        current_sequence=1,
        expiration_date=timezone.now().date() + datetime.timedelta(days=30),
        is_active=True
    )
    
    assert seq.get_next_ncf() == "B0200000001"
    
    # Inactive sequence
    seq.is_active = False
    seq.save()
    assert seq.get_next_ncf() is None
    
    # Reactivate and test exhaustion
    seq.is_active = True
    seq.current_sequence = 11
    seq.save()
    assert seq.get_next_ncf() is None
    
    # Expired sequence
    seq.current_sequence = 5
    seq.expiration_date = timezone.localdate() - datetime.timedelta(days=1)
    seq.save()
    assert seq.get_next_ncf() is None

@pytest.mark.django_db
def test_ncf_sequence_clean_method():
    tenant = Tenant.objects.create(name="Test Tenant", subdomain="test")
    
    # Start greater than end
    seq = NCFSequence(
        tenant=tenant,
        type="02",
        end_sequence=10,
        start_sequence=20,
        expiration_date=timezone.now().date()
    )
    with pytest.raises(ValidationError) as excinfo:
        seq.clean()
    assert "La secuencia inicial no puede ser mayor" in str(excinfo.value)
    
    # Current outside range
    seq2 = NCFSequence(
        tenant=tenant,
        type="02",
        start_sequence=1,
        end_sequence=10,
        current_sequence=12,
        expiration_date=timezone.now().date()
    )
    with pytest.raises(ValidationError) as excinfo:
        seq2.clean()
    assert "La secuencia actual debe estar dentro del rango" in str(excinfo.value)

@pytest.mark.django_db
def test_ncf_sequence_viewset_tenant_isolation(authenticated_user, client, other_tenant, other_user):
    user, api_client = authenticated_user
    user.is_superuser = False
    user.save()
    
    # Assign NCF view permission to user
    from apps.roles_api.models import Role, UserRole
    from django.contrib.auth.models import Permission
    role, _ = Role.objects.get_or_create(name='TestNCFRole', defaults={'description': 'Test role for NCF'})
    perm = Permission.objects.get(codename='view_ncfsequence', content_type__app_label='pos_api')
    role.permissions.add(perm)
    UserRole.objects.create(user=user, role=role, tenant=user.tenant)
    
    # Create sequence for user's tenant
    seq1 = NCFSequence.objects.create(
        tenant=user.tenant,
        type="02",
        prefix="B",
        start_sequence=1,
        end_sequence=100,
        current_sequence=1,
        expiration_date=timezone.now().date() + datetime.timedelta(days=30)
    )
    
    # Create sequence for other tenant
    seq2 = NCFSequence.objects.create(
        tenant=other_tenant,
        type="02",
        prefix="B",
        start_sequence=1,
        end_sequence=100,
        current_sequence=1,
        expiration_date=timezone.now().date() + datetime.timedelta(days=30)
    )
    
    # Authenticate as first user with token to set request.tenant
    from rest_framework_simplejwt.tokens import AccessToken
    token = AccessToken.for_user(user)
    token['tenant_id'] = user.tenant.id
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")
    api_client.force_authenticate(user=user)
    response = api_client.get(reverse("ncf-sequence-list"))
    
    assert response.status_code == status.HTTP_200_OK
    results = response.data.get("results", response.data)
    assert len(results) == 1
    assert results[0]["id"] == seq1.id
    
    # Attempt to access sequence of other tenant directly
    url = reverse("ncf-sequence-detail", kwargs={"pk": seq2.id})
    response = api_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
def test_sale_ncf_generation_consumidor_final(authenticated_user, client):
    user, api_client = authenticated_user
    user.is_superuser = True
    user.save()
    
    # Create open register
    CashRegister.objects.create(
        user=user,
        tenant=user.tenant,
        is_open=True,
        opened_at=timezone.now(),
        initial_cash=0
    )
    
    # Create sequence
    NCFSequence.objects.create(
        tenant=user.tenant,
        type="02",
        prefix="B",
        start_sequence=1,
        end_sequence=10,
        current_sequence=1,
        expiration_date=timezone.now().date() + datetime.timedelta(days=30),
        is_active=True
    )
    
    # Create a real product to pass details validation
    from apps.inventory_api.models import Product
    product = Product.objects.create(
        name="Test Item", sku="TEST01", price=100, stock=10, tenant=user.tenant
    )
    
    data = {
        "total": 100.0,
        "discount": 0.0,
        "paid": 100.0,
        "payment_method": "cash",
        "ncf_type": "02",
        "details": [
            {"content_type": "product", "object_id": product.id, "name": product.name, "quantity": 1, "price": 100.0}
        ],
        "payments": [{"method": "cash", "amount": 100.0}]
    }
    
    api_client.force_authenticate(user=user)
    response = api_client.post(reverse("sale-list"), data, format="json")
    
    assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
    assert response.data["ncf"] == "B0200000001"
    
    # Verify sequence incremented
    seq = NCFSequence.objects.get(tenant=user.tenant, type="02")
    assert seq.current_sequence == 2
    
    # Create second sale and check next NCF
    response = api_client.post(reverse("sale-list"), data, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["ncf"] == "B0200000002"

@pytest.mark.django_db
def test_sale_ncf_generation_credito_fiscal_validation(authenticated_user, client):
    user, api_client = authenticated_user
    user.is_superuser = True
    user.save()
    
    CashRegister.objects.create(
        user=user,
        tenant=user.tenant,
        is_open=True,
        opened_at=timezone.now(),
        initial_cash=0
    )
    
    NCFSequence.objects.create(
        tenant=user.tenant,
        type="01",
        prefix="B",
        start_sequence=1,
        end_sequence=10,
        current_sequence=1,
        expiration_date=timezone.now().date() + datetime.timedelta(days=30),
        is_active=True
    )
    
    from apps.inventory_api.models import Product
    product = Product.objects.create(
        name="Test Item", sku="TEST01", price=100, stock=10, tenant=user.tenant
    )
    
    # Test missing RNC and company name
    data = {
        "total": 100.0,
        "discount": 0.0,
        "paid": 100.0,
        "payment_method": "cash",
        "ncf_type": "01",
        "details": [
            {"content_type": "product", "object_id": product.id, "name": product.name, "quantity": 1, "price": 100.0}
        ],
        "payments": [{"method": "cash", "amount": 100.0}]
    }
    
    api_client.force_authenticate(user=user)
    response = api_client.post(reverse("sale-list"), data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "rnc" in response.data
    
    # Test invalid RNC (not 9 or 11 digits)
    data["rnc"] = "12345"
    data["company_name"] = "Barber Inc"
    response = api_client.post(reverse("sale-list"), data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "rnc" in response.data
    
    # Test successful creation with 9-digit RNC
    data["rnc"] = "131123456"
    response = api_client.post(reverse("sale-list"), data, format="json")
    assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
    assert response.data["ncf"] == "B0100000001"
    assert response.data["rnc"] == "131123456"
    assert response.data["company_name"] == "Barber Inc"

@pytest.mark.django_db
def test_sale_ncf_exhausted_error(authenticated_user, client):
    user, api_client = authenticated_user
    user.is_superuser = True
    user.save()
    
    CashRegister.objects.create(
        user=user,
        tenant=user.tenant,
        is_open=True,
        opened_at=timezone.now(),
        initial_cash=0
    )
    
    # Create sequence already at the end
    NCFSequence.objects.create(
        tenant=user.tenant,
        type="02",
        prefix="B",
        start_sequence=1,
        end_sequence=10,
        current_sequence=11,
        expiration_date=timezone.now().date() + datetime.timedelta(days=30),
        is_active=True
    )
    
    from apps.inventory_api.models import Product
    product = Product.objects.create(
        name="Test Item", sku="TEST01", price=100, stock=10, tenant=user.tenant
    )
    
    data = {
        "total": 100.0,
        "discount": 0.0,
        "paid": 100.0,
        "payment_method": "cash",
        "ncf_type": "02",
        "details": [
            {"content_type": "product", "object_id": product.id, "name": product.name, "quantity": 1, "price": 100.0}
        ],
        "payments": [{"method": "cash", "amount": 100.0}]
    }
    
    api_client.force_authenticate(user=user)
    response = api_client.post(reverse("sale-list"), data, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "ncf_type" in str(response.data) or "non_field_errors" in response.data or response.status_code == 400
