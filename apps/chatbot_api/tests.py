from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


class ChatBotTests(TestCase):
    """Pruebas unitarias para el endpoint del Chatbot Inteligente."""

    def setUp(self):
        self.client = APIClient()

    def test_chatbot_endpoint_is_public(self):
        """Verifica que el chatbot sea de acceso público (AllowAny)."""
        response = self.client.post("/api/chatbot/", {"prompt": "Hola"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("reply", response.data)

    def test_chatbot_validation_empty_prompt(self):
        """Verifica que la API retorne 400 Bad Request si el prompt está vacío."""
        response = self.client.post("/api/chatbot/", {"prompt": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("prompt", response.data)

    def test_chatbot_validation_missing_prompt(self):
        """Verifica que la API retorne 400 Bad Request si falta el campo prompt."""
        response = self.client.post("/api/chatbot/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("prompt", response.data)

    def test_chatbot_fallback_responses(self):
        """Verifica las respuestas inteligentes del motor de fallback local."""
        # Saludo
        response = self.client.post("/api/chatbot/", {"prompt": "Hola, buenos días"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("💈✨", response.data["reply"])

        # Precios
        response = self.client.post("/api/chatbot/", {"prompt": "cuánto cuesta la suscripción?"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Plan Pro", response.data["reply"])
        self.assertIn("$69.99", response.data["reply"])

        # NCF / Facturación
        response = self.client.post("/api/chatbot/", {"prompt": "tienen soporte NCF DGII?"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("DGII", response.data["reply"])
        self.assertIn("Crédito Fiscal", response.data["reply"])

        # General
        response = self.client.post("/api/chatbot/", {"prompt": "alguna otra cosa?"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Auron Suite es la plataforma", response.data["reply"])
