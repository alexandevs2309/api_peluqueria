import json
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from apps.auth_api.factories import UserFactory
from apps.clients_api.models import Client
from apps.clients_api.serializers import ClientSerializer

@pytest.mark.django_db
class TestClientAPI:

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def auth_client(self):
        from apps.tenants_api.models import Tenant
        tenant = Tenant.objects.create(
            name="Test Client Tenant",
            subdomain="test-clients-api"
        )
        user = UserFactory(
            is_email_verified=True,
            is_superuser=True,
            tenant=tenant
        )
        client = APIClient()
        client.force_authenticate(user=user)
        return client, user

    @pytest.fixture
    def client_obj(self, auth_client):
        client, user = auth_client
        return Client.objects.create(
            user=user,
            tenant=user.tenant,
            full_name="Juan Pérez",
            email="juan@example.com",
            phone="+123456789",
            notes="Cliente frecuente",
            created_by=user
        )

    def test_create_client(self, auth_client):
        client, user = auth_client
        url = reverse('client-list')
        print("\n--- USUARIO AUTENTICADO ---")
        print(f"Usuario: {user}, ID: {user.id}, Autenticado: {user.is_authenticated}")

        payload = {
            "full_name": "María García",
            "email": "maria@example.com",
            "phone": "+123456700",
            "notes": "Cliente nueva"
        }
        print("\n--- Datos para CREAR CLIENTE ---")
        print(payload)

        response = client.post(url, payload, format='json')
        print("\n--- RESPUESTA CREAR CLIENTE ---")
        print("Status Code:", response.status_code)
        try:
            print("Content (JSON):", response.json())
        except json.JSONDecodeError:
            print("Content (Text):", response.content)
        assert response.status_code == status.HTTP_201_CREATED
        assert Client.objects.filter(email="maria@example.com").exists()

    def test_list_clients(self, auth_client, client_obj):
        client, user = auth_client
        url = reverse('client-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_retrieve_client(self, auth_client, client_obj):
        client, user = auth_client
        url = reverse('client-detail', args=[client_obj.id])
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == client_obj.email

    def test_update_client(self, auth_client, client_obj):
        client, user = auth_client
        url = reverse('client-detail', args=[client_obj.id])
        update_payload = {
            "full_name": "Juan Actualizado",
            "email": client_obj.email,
            "phone": client_obj.phone
        }

        print("\n--- Datos para ACTUALIZAR CLIENTE ---")
        print(update_payload)

        response = client.patch(url, update_payload, format='json')
        print("\n--- RESPUESTA ACTUALIZAR CLIENTE ---")
        print("Status Code:", response.status_code)
        try:
            print("Content (JSON):", response.json())
        except json.JSONDecodeError:
            print("Content (Text):", response.content)
        assert response.status_code == status.HTTP_200_OK
        client_obj.refresh_from_db()
        assert client_obj.full_name == "Juan Actualizado"

    def test_delete_client(self, auth_client, client_obj):
        client, user = auth_client
        url = reverse('client-detail', args=[client_obj.id])
        response = client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Client.objects.filter(id=client_obj.id).exists()

    def test_xss_full_name_sanitized_on_create(self, auth_client):
        client, user = auth_client
        url = reverse('client-list')
        xss_payload = '<script>alert("xss")</script>Juan Perez'
        payload = {
            "full_name": xss_payload,
            "email": "xss_create@test.com",
            "phone": "+18095551234",
        }
        response = client.post(url, payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert '<script>' not in response.data['full_name']
        assert 'Juan Perez' in response.data['full_name']
        db_client = Client.objects.get(id=response.data['id'])
        assert '<script>' not in db_client.full_name

    def test_xss_full_name_sanitized_on_update(self, auth_client):
        client, user = auth_client
        url = reverse('client-list')
        create_payload = {
            "full_name": "Maria Test",
            "email": "xss_update@test.com",
            "phone": "+18095551235",
        }
        create_response = client.post(url, create_payload, format='json')
        assert create_response.status_code == status.HTTP_201_CREATED
        client_id = create_response.data['id']

        update_url = reverse('client-detail', args=[client_id]) + f'?tenant={user.tenant.id}'
        xss_payload = '<img src=x onerror=alert(1)>Maria Actualizada'
        payload = {"full_name": xss_payload, "email": "xss_update@test.com"}
        response = client.patch(update_url, payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert '<img' not in response.data['full_name']
        assert 'Maria Actualizada' in response.data['full_name']

    def test_xss_full_name_preserves_legitimate_chars(self, auth_client):
        client, user = auth_client
        url = reverse('client-list')
        legitimate_names = [
            "José María",
            "Müller",
            "O'Conner",
            "Nguyễn Văn A",
            "Jean-Pierre",
            "Ana Sofía García-López",
            "Carlos Jr.",
        ]
        for i, name in enumerate(legitimate_names):
            payload = {
                "full_name": name,
                "email": f"legit_{i}@test.com",
                "phone": f"+1809{5550000 + i}",
            }
            response = client.post(url, payload, format='json')
            assert response.status_code == status.HTTP_201_CREATED, f"Failed for name: {name}: {response.data}"
            assert response.data['full_name'] == name, f"Name corrupted: {name} -> {response.data['full_name']}"

    def test_xss_various_payloads_sanitized(self, auth_client):
        client, user = auth_client
        url = reverse('client-list')
        payloads = [
            ('<b>Bold Name</b>', 'Bold Name'),
            ('<div onclick="steal()">Click</div>', 'Click'),
            ('<svg onload=alert(1)>Test', 'Test'),
            ('<a href="javascript:alert(1)">Link</a>Link', 'LinkLink'),
            ('  <i>  Trimmed  </i>  ', 'Trimmed'),
        ]
        for i, (xss_input, expected) in enumerate(payloads):
            payload = {
                "full_name": xss_input,
                "email": f"xss_{i}@test.com",
                "phone": f"+1809{5560000 + i}",
            }
            response = client.post(url, payload, format='json')
            assert response.status_code == status.HTTP_201_CREATED, f"Failed for: {xss_input}"
            assert response.data['full_name'] == expected, f"Expected '{expected}', got '{response.data['full_name']}'"
