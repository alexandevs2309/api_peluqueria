import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.tenants_api.models import Tenant

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        email="admin@test.com", 
        password="testpass123", 
        full_name="Admin User"
    )


@pytest.fixture
def regular_user():
    return User.objects.create_user(
        email="user@test.com", 
        password="testpass123", 
        full_name="Regular User"
    )


@pytest.fixture
def tenant_data():
    return {
        "name": "Test Tenant",
        "subdomain": "test-tenant",
        "plan_type": "basic",
        "subscription_status": "trial",
        "max_employees": 10,
        "max_users": 50,
        "is_active": True
    }


@pytest.fixture
def tenant(admin_user):
    return Tenant.objects.create(
        name="Existing Tenant",
        subdomain="existing-tenant",
        owner=admin_user,
        plan_type="premium",
        subscription_status="active",
        max_employees=20,
        max_users=100,
        is_active=True
    )


@pytest.mark.django_db
class TestTenantViewSet:
    
    def test_list_tenants_as_admin(self, api_client, admin_user, tenant):
        api_client.force_authenticate(user=admin_user)
        url = reverse("tenant-list")
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert response.data[0]["name"] == tenant.name
    
    def test_list_tenants_as_regular_user(self, api_client, regular_user, tenant):
        api_client.force_authenticate(user=regular_user)
        url = reverse("tenant-list")
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # Regular users should only see tenants they own
        assert len(response.data) == 0
    
    def test_create_tenant_as_admin(self, api_client, admin_user, tenant_data):
        api_client.force_authenticate(user=admin_user)
        url = reverse("tenant-list")
        response = api_client.post(url, tenant_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == tenant_data["name"]
        assert response.data["subdomain"] == tenant_data["subdomain"]
        assert response.data["owner"] == admin_user.id
    
    def test_create_tenant_with_duplicate_subdomain(self, api_client, admin_user, tenant, tenant_data):
        api_client.force_authenticate(user=admin_user)
        tenant_data["subdomain"] = tenant.subdomain  # Use existing subdomain
        url = reverse("tenant-list")
        response = api_client.post(url, tenant_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "subdomain" in response.data
    
    def test_retrieve_tenant(self, api_client, admin_user, tenant):
        api_client.force_authenticate(user=admin_user)
        url = reverse("tenant-detail", kwargs={"pk": tenant.pk})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == tenant.name
        assert response.data["subdomain"] == tenant.subdomain
    
    def test_update_tenant(self, api_client, admin_user, tenant):
        api_client.force_authenticate(user=admin_user)
        url = reverse("tenant-detail", kwargs={"pk": tenant.pk})
        update_data = {"name": "Updated Tenant Name"}
        response = api_client.patch(url, update_data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Tenant Name"
    
    def test_delete_tenant(self, api_client, admin_user, tenant):
        api_client.force_authenticate(user=admin_user)
        url = reverse("tenant-detail", kwargs={"pk": tenant.pk})
        response = api_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Tenant.objects.filter(pk=tenant.pk).exists()
    
    def test_activate_tenant(self, api_client, admin_user, tenant):
        tenant.is_active = False
        tenant.save()
        
        api_client.force_authenticate(user=admin_user)
        url = reverse("tenant-activate", kwargs={"pk": tenant.pk})
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        tenant.refresh_from_db()
        assert tenant.is_active == True
    
    def test_deactivate_tenant(self, api_client, admin_user, tenant):
        api_client.force_authenticate(user=admin_user)
        url = reverse("tenant-deactivate", kwargs={"pk": tenant.pk})
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        tenant.refresh_from_db()
        assert tenant.is_active == False
    
    def test_tenant_stats(self, api_client, admin_user, tenant):
        api_client.force_authenticate(user=admin_user)
        url = reverse("tenant-stats", kwargs={"pk": tenant.pk})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert "max_employees" in response.data
        assert "max_users" in response.data
        assert response.data["max_employees"] == tenant.max_employees
        assert response.data["max_users"] == tenant.max_users


@pytest.mark.django_db
class TestTenantModel:
    
    def test_tenant_creation(self, admin_user):
        tenant = Tenant.objects.create(
            name="Test Tenant",
            subdomain="test-tenant",
            owner=admin_user,
            plan_type="basic",
            subscription_status="trial"
        )
        
        assert tenant.name == "Test Tenant"
        assert tenant.subdomain == "test-tenant"
        assert tenant.owner == admin_user
        assert tenant.plan_type == "basic"
        assert tenant.subscription_status == "trial"
        assert tenant.is_active == True
    
    def test_tenant_string_representation(self, admin_user):
        tenant = Tenant.objects.create(
            name="Test Tenant",
            subdomain="test-tenant",
            owner=admin_user
        )
        
        assert str(tenant) == "Test Tenant (test-tenant)"
    
    def test_tenant_unique_subdomain(self, admin_user):
        Tenant.objects.create(
            name="Tenant 1",
            subdomain="unique-subdomain",
            owner=admin_user
        )
        
        with pytest.raises(Exception):
            Tenant.objects.create(
                name="Tenant 2",
                subdomain="unique-subdomain",  # Same subdomain
                owner=admin_user
            )
