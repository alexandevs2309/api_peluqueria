import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.auth_api.factories import UserFactory
from apps.auth_api.models import User
from apps.settings_api.models import Setting, Branch, SettingsAuditLog
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from apps.settings_api.serializers import SettingSerializer
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan

@pytest.mark.django_db
class TestSettingsAPI:

    @pytest.fixture(scope="session")
    def generate_test_image(self, tmp_path_factory):
        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
        temp_dir = tmp_path_factory.mktemp("data")
        file_path = temp_dir / "test_image.png"
        img.save(file_path)
        return str(file_path)

    @pytest.fixture
    def logo_file(self, generate_test_image):
        with open(generate_test_image, "rb") as f:
            return SimpleUploadedFile("test_image.png", f.read(), content_type="image/png")

    @pytest.fixture
    def plan(self):
        return SubscriptionPlan.objects.create(
            name="premium",
            price=10.0,
            max_users=10,
            features={"custom_branding": True}
        )

    @pytest.fixture
    def tenant(self, plan):
        return Tenant.objects.create(name="Test Tenant", subdomain="test-tenant", subscription_plan=plan)

    @pytest.fixture
    def admin_user(self, tenant):
        # Creamos un usuario Client-Admin (no superusuario de Django) con su tenant asociado
        user = User.objects.create_user(
            email="admin@admin.com", 
            full_name="Admin User", 
            password="admin123",
            tenant=tenant,
            role="Client-Admin"
        )
        
        # Asignamos el rol y los permisos de settings_api
        from apps.roles_api.models import Role, UserRole
        from django.contrib.auth.models import Permission
        role, _ = Role.objects.get_or_create(name="Client-Admin", defaults={'description': 'Admin role'})
        perms = Permission.objects.filter(content_type__app_label='settings_api')
        role.permissions.add(*perms)
        UserRole.objects.get_or_create(user=user, role=role, tenant=tenant)
        
        return user

    @pytest.fixture
    def normal_user(self, tenant):
        return User.objects.create_user(email="user@user.com", full_name="Normal User", password="user123", tenant=tenant)

    @pytest.fixture
    def api_client_admin(self, admin_user, tenant):
        from apps.auth_api.views import issue_refresh_for_user
        _, access_token = issue_refresh_for_user(admin_user, tenant)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(access_token)}')
        client.force_authenticate(user=admin_user)
        return client

    @pytest.fixture
    def api_client_user(self, normal_user, tenant):
        from apps.auth_api.views import issue_refresh_for_user
        _, access_token = issue_refresh_for_user(normal_user, tenant)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(access_token)}')
        client.force_authenticate(user=normal_user)
        return client

    def test_get_setting_admin(self, api_client_admin, tenant):
        from apps.settings_api.barbershop_models import BarbershopSettings
        setting, _ = BarbershopSettings.objects.get_or_create(tenant=tenant, name="Mi Peluquería")
        url = reverse("barbershop-settings-list")
        response = api_client_admin.get(url)
        assert response.status_code == 200
        assert response.data["name"] == "Mi Peluquería"

    def test_get_setting_user_forbidden(self, api_client_user, tenant):
        # Un usuario normal sin permisos (view_barbershopsettings) recibe 403.
        url = reverse("barbershop-settings-list")
        response = api_client_user.get(url)
        assert response.status_code == 403

    def test_update_setting_admin(self, api_client_admin, tenant):
        from apps.settings_api.barbershop_models import BarbershopSettings
        setting, _ = BarbershopSettings.objects.get_or_create(tenant=tenant, name="Mi Peluquería")
        url = reverse("barbershop-settings-list")
        response = api_client_admin.post(url, {
            "name": "Nueva Peluquería",
            "currency": "USD",
            "currency_symbol": "$",
            "confirmed_critical": True,
            "business_hours": {
                "monday": {"open": "08:00", "close": "18:00", "closed": False},
                "tuesday": {"open": "08:00", "close": "18:00", "closed": False},
                "wednesday": {"open": "08:00", "close": "18:00", "closed": False},
                "thursday": {"open": "08:00", "close": "18:00", "closed": False},
                "friday": {"open": "08:00", "close": "18:00", "closed": False},
                "saturday": {"open": "08:00", "close": "16:00", "closed": False},
                "sunday": {"open": "10:00", "close": "14:00", "closed": True}
            },
            "contact": {}
        }, format="json")
        assert response.status_code == 200
        setting.refresh_from_db()
        assert setting.name == "Nueva Peluquería"

    def test_update_setting_user_forbidden(self, api_client_user, tenant):
        url = reverse("barbershop-settings-list")
        response = api_client_user.post(url, {"name": "Hackeado"}, format="json")
        assert response.status_code == 403

    def test_upload_logo(self, api_client_admin, tenant, logo_file):
        url = reverse("barbershop-settings-upload-logo")
        response = api_client_admin.post(
            url,
            data={"logo": logo_file},
            format="multipart"
        )
        assert response.status_code == 200
        assert "logo_url" in response.data

    def test_audit_log_created_on_update(self, api_client_admin, tenant):
        from apps.settings_api.barbershop_models import BarbershopSettings
        setting, _ = BarbershopSettings.objects.get_or_create(tenant=tenant, currency="COP")
        
        url = reverse("barbershop-settings-list")
        old_audit_count = SettingsAuditLog.objects.count()
        response = api_client_admin.post(url, {
            "name": "Audit Test",
            "currency": "USD",
            "currency_symbol": "$",
            "confirmed_critical": True,
            "business_hours": {
                "monday": {"open": "08:00", "close": "18:00", "closed": False},
                "tuesday": {"open": "08:00", "close": "18:00", "closed": False},
                "wednesday": {"open": "08:00", "close": "18:00", "closed": False},
                "thursday": {"open": "08:00", "close": "18:00", "closed": False},
                "friday": {"open": "08:00", "close": "18:00", "closed": False},
                "saturday": {"open": "08:00", "close": "16:00", "closed": False},
                "sunday": {"open": "10:00", "close": "14:00", "closed": True}
            },
            "contact": {}
        }, format="json")
        assert response.status_code == 200
        new_audit_count = SettingsAuditLog.objects.count()
        assert new_audit_count == old_audit_count + 1
        log = SettingsAuditLog.objects.latest('id')
        assert log.user.email == "admin@admin.com"
        assert log.field_name == "currency"
        assert log.old_value == "COP"
        assert log.new_value == "USD"

    def test_whatsapp_status(self, api_client_admin, tenant):
        url = reverse("barbershop-settings-whatsapp-status")
        response = api_client_admin.get(url)
        assert response.status_code == 200
        assert "whatsapp_enabled" in response.data
        assert "whatsapp_status" in response.data

    def test_whatsapp_connect_forbidden_if_no_feature(self, api_client_admin, tenant):
        url = reverse("barbershop-settings-whatsapp-connect")
        response = api_client_admin.post(url, {})
        assert response.status_code == 403

    def test_whatsapp_connect_success(self, api_client_admin, tenant, monkeypatch):
        # Activar feature flag
        tenant.subscription_plan.features["whatsapp_notifications"] = True
        tenant.subscription_plan.save()

        from unittest.mock import MagicMock
        mock_provider = MagicMock()
        mock_provider.create_instance.return_value = {
            "success": True,
            "token": "test-token",
            "qrcode_base64": "dummy-base64",
            "qrcode_code": "dummy-code"
        }
        
        import apps.settings_api.whatsapp_provider as provider_module
        monkeypatch.setattr(provider_module, "get_whatsapp_provider", lambda: mock_provider)

        url = reverse("barbershop-settings-whatsapp-connect")
        response = api_client_admin.post(url, {})
        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["qrcode_base64"] == "dummy-base64"

    def test_whatsapp_disconnect(self, api_client_admin, tenant, monkeypatch):
        from unittest.mock import MagicMock
        mock_provider = MagicMock()
        mock_provider.delete_instance.return_value = True
        
        import apps.settings_api.whatsapp_provider as provider_module
        monkeypatch.setattr(provider_module, "get_whatsapp_provider", lambda: mock_provider)

        url = reverse("barbershop-settings-whatsapp-disconnect")
        response = api_client_admin.post(url, {})
        assert response.status_code == 200
        assert response.data["success"] is True


    def test_whatsapp_webhook_public(self, client, tenant):
        from apps.settings_api.barbershop_models import BarbershopSettings
        settings, _ = BarbershopSettings.objects.get_or_create(
            tenant=tenant, 
            whatsapp_instance_name="tenant_test"
        )
        
        url = reverse("barbershop-settings-whatsapp-webhook")
        payload = {
            "event": "connection.update",
            "instance": "tenant_test",
            "data": {
                "state": "open",
                "phone": "123456789"
            }
        }
        response = client.post(url, payload, content_type="application/json")
        assert response.status_code == 200
        settings.refresh_from_db()
        assert settings.whatsapp_status == "connected"
        assert settings.whatsapp_enabled is True
        assert settings.whatsapp_phone == "123456789"


@pytest.mark.django_db

def test_no_duplicate_settings_per_branch():
    tenant = Tenant.objects.create(name="Tenant Branch Test", subdomain="tenant-branch-test")
    branch = Branch.objects.create(name="Sucursal 1", tenant=tenant)
    Setting.objects.create(branch=branch, business_name="Empresa 1")
    with pytest.raises((ValueError, IntegrityError)):
        Setting.objects.create(branch=branch, business_name="Empresa 2")

@pytest.mark.django_db
def test_validate_business_hours_invalid_format():
    tenant = Tenant.objects.create(name="Tenant Branch Test B", subdomain="tenant-branch-test-b")
    branch = Branch.objects.create(name="Sucursal A", tenant=tenant)
    data = {
        "branch": branch.id,
        "business_name": "Negocio Test",
        "business_hours": "9-5"
    }
    serializer = SettingSerializer(data=data)
    with pytest.raises(ValidationError) as exc:
        serializer.is_valid(raise_exception=True)
    assert "horario" in str(exc.value).lower()

@pytest.mark.django_db
def test_validate_business_hours_invalid_day_format():
    tenant = Tenant.objects.create(name="Tenant Branch Test C", subdomain="tenant-branch-test-c")
    branch = Branch.objects.create(name="Sucursal B", tenant=tenant)
    data = {
        "branch": branch.id,
        "business_name": "Negocio Test",
        "business_hours": {"lunes": 123}
    }
    serializer = SettingSerializer(data=data)
    with pytest.raises(ValidationError) as exc:
        serializer.is_valid(raise_exception=True)
    assert "formato" in str(exc.value).lower()

@pytest.mark.django_db
def test_setting_unique_branch_constraint():
    tenant = Tenant.objects.create(name="Tenant Branch Test D", subdomain="tenant-branch-test-d")
    branch = Branch.objects.create(name="Sucursal Única", tenant=tenant)
    Setting.objects.create(branch=branch, business_name="Negocio 1")
    with pytest.raises((ValueError, IntegrityError)):
        Setting.objects.create(branch=branch, business_name="Negocio 2")