from django.test import TestCase
from rest_framework.test import APIClient

from apps.mcp_api.views import _detect_tool_offline


class McpIntentDetectionTests(TestCase):
    def test_sales_today(self):
        tool, params = _detect_tool_offline("¿cuánto vendí hoy?")
        self.assertEqual(tool, "sales_summary")
        self.assertEqual(params["period"], "today")

    def test_sales_week(self):
        tool, params = _detect_tool_offline("ventas de la semana")
        self.assertEqual(tool, "sales_summary")
        self.assertEqual(params["period"], "week")

    def test_sales_month(self):
        tool, params = _detect_tool_offline("ingresos del mes")
        self.assertEqual(tool, "sales_summary")
        self.assertEqual(params["period"], "month")

    def test_appointments_tomorrow(self):
        tool, params = _detect_tool_offline("citas de mañana")
        self.assertEqual(tool, "appointments_list")
        self.assertIsNotNone(params.get("day"))

    def test_appointments_today_with_status(self):
        tool, params = _detect_tool_offline("citas pendientes de hoy")
        self.assertEqual(tool, "appointments_list")
        self.assertEqual(params.get("status"), "scheduled")
        self.assertIsNotNone(params.get("day"))

    def test_clients_search_extracts_query(self):
        tool, params = _detect_tool_offline("buscar cliente Juan Pérez")
        self.assertEqual(tool, "clients_search")
        query = params["query"].lower()
        self.assertIn("juan", query)
        self.assertIn("perez", query)

    def test_inventory(self):
        tool, _ = _detect_tool_offline("stock bajo")
        self.assertEqual(tool, "inventory_alerts")

    def test_performance(self):
        tool, params = _detect_tool_offline("rendimiento de empleados de esta semana")
        self.assertEqual(tool, "employee_performance")
        self.assertEqual(params["period"], "week")

    def test_no_intent(self):
        tool, _ = _detect_tool_offline("qué hay de nuevo?")
        self.assertIsNone(tool)


class McpChatAuthTests(TestCase):
    def test_chat_requires_auth(self):
        client = APIClient()
        resp = client.post("/api/mcp/chat/", {"message": "hola"}, format="json")
        self.assertIn(resp.status_code, (401, 403))

    def test_chat_requires_message(self):
        from apps.auth_api.factories import UserFactory
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.post("/api/mcp/chat/", {}, format="json")
        self.assertEqual(resp.status_code, 400)