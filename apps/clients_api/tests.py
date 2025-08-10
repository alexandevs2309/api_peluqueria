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
        user = UserFactory(is_email_verified=True)
        client = APIClient()
        client.force_authenticate(user=user)
        return client, user

    @pytest.fixture
    def client_obj(self, auth_client):
        client, user = auth_client
        return Client.objects.create(
            user=user,
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