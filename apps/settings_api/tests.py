import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.auth_api.factories import UserFactory
from apps.auth_api.models import User
from apps.settings_api.models import Setting, Branch, SettingAuditLog
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from PIL import Image
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError
from apps.settings_api.serializers import SettingSerializer
from apps.settings_api.models import Branch

@pytest.mark.django_db
class TestSettingsAPI:


    @pytest.fixture(scope="session")
    def generate_test_image(self, tmp_path_factory):
        # Crea imagen real y la guarda en un archivo temporal
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
    def admin_user(self):
        return User.objects.create_superuser(email="admin@admin.com", full_name="Admin User", password="admin123")

    @pytest.fixture
    def normal_user(self):
        return User.objects.create_user(email="user@user.com", full_name="Normal User", password="user123")

    @pytest.fixture
    def api_client_admin(self, admin_user):
        client = APIClient()
        client.force_authenticate(user=admin_user)
        return client

    @pytest.fixture
    def api_client_user(self, normal_user):
        client = APIClient()
        client.force_authenticate(user=normal_user)
        return client

    @pytest.fixture
    def branch(self):
        return Branch.objects.create(name="Sucursal 1", address="Calle 123")

    @pytest.fixture
    def setting(self, branch):
        return Setting.objects.create(
            branch=branch,
            business_name="Mi Peluquería",
            business_email="contacto@peluqueria.com",
            phone_number="123456789",
            address="Av. Siempre Viva 742",
            currency="DOP",
            tax_percentage=18.00,
            timezone="America/Santo_Domingo",
            business_hours={"monday": "9:00-18:00"},
            preferences={"notifications": True},
            theme="light",
        )

    def test_get_setting_admin(self, api_client_admin, setting, branch):
        url = reverse("setting-detail") + f"?branch={branch.id}"
        response = api_client_admin.get(url)
        assert response.status_code == 200
        assert response.data["business_name"] == setting.business_name

    def test_get_setting_user_forbidden(self, api_client_user, setting, branch):
        url = reverse("setting-detail") + f"?branch={branch.id}"
        response = api_client_user.get(url)
        # Permiso IsAdminUser debería bloquear GET para usuario normal
        assert response.status_code == 403

    def test_update_setting_admin(self, api_client_admin, setting, branch):
        url = reverse("setting-detail") + f"?branch={branch.id}"
        response = api_client_admin.patch(url, {"business_name": "Nueva Peluquería"})
        assert response.status_code == 200
        setting.refresh_from_db()
        assert setting.business_name == "Nueva Peluquería"

    def test_update_setting_user_forbidden(self, api_client_user, setting, branch):
        url = reverse("setting-detail") + f"?branch={branch.id}"
        response = api_client_user.patch(url, {"business_name": "Hackeado"})
        assert response.status_code == 403
        setting.refresh_from_db()
        assert setting.business_name != "Hackeado"

    def test_upload_logo(self, api_client_admin, setting, branch, logo_file):
        url = reverse("setting-detail") + f"?branch={branch.id}"
        response = api_client_admin.patch(
            url,
            data={"logo": logo_file},
            format="multipart"
        )
        print("Status code:", response.status_code)
        print("Response data:", response.data)
        assert response.status_code == 200, f"Error response data: {response.data}"
        assert response.data["logo"] is not None

        assert response.status_code == 200, f"Error response data: {response.data}"
        assert response.data["logo"] is not None


    def test_export_setting(self, api_client_admin, setting, branch):
        url = reverse("setting-export") + f"?branch={branch.id}"
        response = api_client_admin.get(url)
        assert response.status_code == 200
        assert response.data["business_name"] == setting.business_name

    def test_export_setting_not_found(self, api_client_admin):
        url = reverse("setting-export") + "?branch=99999"
        response = api_client_admin.get(url)
        assert response.status_code == 404

    def test_import_setting(self, api_client_admin, branch):
        url = reverse("setting-import")
        data = {
            "branch": branch.id,
            "business_name": "Peluquería Importada",
            "business_email": "import@peluqueria.com",
            "phone_number": "5555555",
            "address": "Calle Importada 1",
            "currency": "USD",
            "tax_percentage": "12.00",
            "timezone": "America/New_York",
            "business_hours": {"tuesday": "10:00-17:00"},
            "preferences": {"notifications": False},
            "theme": "dark",
        }
        response = api_client_admin.post(url, data, format="json")
        assert response.status_code == 200
        setting = Setting.objects.filter(branch=branch).first()
        assert setting.business_name == "Peluquería Importada"
        assert setting.theme == "dark"

    def test_audit_log_created_on_update(self, api_client_admin, setting, branch):
        url = reverse("setting-detail") + f"?branch={branch.id}"
        old_audit_count = SettingAuditLog.objects.count()
        response = api_client_admin.patch(url, {"business_name": "Audit Test"})
        assert response.status_code == 200
        new_audit_count = SettingAuditLog.objects.count()
        assert new_audit_count == old_audit_count + 1
        log = SettingAuditLog.objects.latest('changed_at')
        assert log.changed_by.email == "admin@admin.com"
        assert log.change_summary["new"]["business_name"] == "Audit Test"

    def test_cache_used(self, api_client_admin, setting, branch):
        cache_key = f"setting_{branch.id}"
        cache.delete(cache_key)
        url = reverse("setting-detail") + f"?branch={branch.id}"
        # Primera llamada debería cargar en cache
        response1 = api_client_admin.get(url)
        assert response1.status_code == 200
        cached = cache.get(cache_key)
        assert cached is not None
        # Segunda llamada usa cache
        response2 = api_client_admin.get(url)
        assert response2.status_code == 200


@pytest.fixture
def admin_client(db):
    user = UserFactory(is_superuser=True, is_email_verified=True)
    client = APIClient()
    client.force_authenticate(user=user)
    return client

@pytest.mark.django_db
def test_create_setting_missing_fields(admin_client):
    response = admin_client.post(reverse('setting-detail'), {}, format='json')
    assert response.status_code == 403

@pytest.mark.django_db
def test_create_setting_invalid_values(admin_client):
    data = {
        "key": "",  # required field empty
        "value": "SomeValue",
        "description": "Test"
    }
    response = admin_client.post(reverse('setting-detail'), data, format='json')
    assert response.status_code == 403


@pytest.mark.django_db
def test_create_setting_missing_required_fields(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    response = client.post(reverse("setting-list-create"), {"value": "X"}, format="json")
    assert response.status_code == 400
    assert 'business_name' in response.data
    assert 'branch' in response.data


@pytest.mark.django_db
def test_no_duplicate_settings_per_branch():
    branch = Branch.objects.create(name="Sucursal 1")
    Setting.objects.create(branch=branch, business_name="Empresa 1")
    with pytest.raises(ValueError):
        Setting.objects.create(branch=branch, business_name="Empresa 2")

@pytest.mark.django_db
def test_validate_business_hours_invalid_format():
    branch = Branch.objects.create(name="Sucursal A")
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
    branch = Branch.objects.create(name="Sucursal B")
    data = {
        "branch": branch.id,
        "business_name": "Negocio Test",
        "business_hours": {"lunes": 123}
    }
    serializer = SettingSerializer(data=data)
    with pytest.raises(ValidationError) as exc:
        serializer.is_valid(raise_exception=True)
    assert "formato inválido" in str(exc.value).lower()

@pytest.mark.django_db
def test_setting_unique_branch_constraint():
    branch = Branch.objects.create(name="Sucursal Única")
    Setting.objects.create(branch=branch, business_name="Negocio 1")
    with pytest.raises(ValueError) as exc:
        Setting.objects.create(branch=branch, business_name="Negocio 2")
    assert "solo puede existir un setting" in str(exc.value).lower()