from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from apps.auth_api.factories import UserFactory
from apps.mcp_api.llm import _resolve_provider, run_tool_chat
from apps.mcp_api.models import TenantAiCredential
from apps.mcp_api.views import TenantAiCredentialView, _detect_tool_offline
from apps.tenants_api.models import Tenant


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
        user = UserFactory(is_superuser=True)
        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.post("/api/mcp/chat/", {}, format="json")
        self.assertEqual(resp.status_code, 400)


class TenantAiCredentialModelTests(TestCase):
    def test_key_is_encrypted_and_masked(self):
        cred = TenantAiCredential(tenant=UserFactory().tenant)
        cred.set_api_key('clave-super-secreta-1234')
        self.assertNotIn('clave-super-secreta-1234', cred.encrypted_api_key)
        self.assertEqual(cred.get_api_key(), 'clave-super-secreta-1234')
        self.assertEqual(cred.key_hint, '••••1234')

    def test_plain_text_is_never_stored(self):
        cred = TenantAiCredential.objects.create(
            tenant=UserFactory().tenant, mode=TenantAiCredential.MODE_BYOK
        )
        cred.set_api_key('AIzaSy-clave-de-prueba')
        cred.save()
        cred.refresh_from_db()
        self.assertNotIn('AIzaSy', cred.encrypted_api_key)
        self.assertEqual(cred.get_api_key(), 'AIzaSy-clave-de-prueba')

    def test_quota_is_limited_and_period_resets(self):
        cred = TenantAiCredential.objects.create(
            tenant=UserFactory().tenant,
            mode=TenantAiCredential.MODE_INCLUDED,
            monthly_request_limit=2,
            period_month='2026-01',
            requests_this_month=99,
        )
        self.assertTrue(cred.consume_request())
        self.assertEqual(cred.requests_this_month, 1)
        self.assertTrue(cred.consume_request())
        self.assertFalse(cred.consume_request())
        cred.period_month = '2025-12'
        cred.save()
        self.assertTrue(cred.consume_request())
        self.assertEqual(cred.requests_this_month, 1)


@override_settings(GEMINI_API_KEY='clave-global-del-producto', LLM_PROVIDER='', LLM_API_KEY='')
class TenantAiCredentialProviderTests(TestCase):
    def setUp(self):
        self.tenant_a = Tenant.objects.create(name='A', subdomain='tenant-a')
        self.tenant_b = Tenant.objects.create(name='B', subdomain='tenant-b')

    def test_without_configuration_uses_global_key(self):
        cfg = _resolve_provider(self.tenant_a)
        self.assertEqual(cfg['source'], 'global')
        self.assertEqual(cfg['key'], 'clave-global-del-producto')

    def test_byok_uses_tenant_key(self):
        cred = TenantAiCredential.objects.create(tenant=self.tenant_a)
        cred.set_api_key('clave-del-negocio-a')
        cred.save()
        cfg = _resolve_provider(self.tenant_a)
        self.assertEqual(cfg['source'], 'byok')
        self.assertEqual(cfg['key'], 'clave-del-negocio-a')
        self.assertEqual(_resolve_provider(self.tenant_b)['key'], 'clave-global-del-producto')

    def test_byok_without_key_does_not_fall_back_to_global(self):
        TenantAiCredential.objects.create(tenant=self.tenant_a, mode=TenantAiCredential.MODE_BYOK)
        self.assertIsNone(_resolve_provider(self.tenant_a))

    def test_included_mode_stops_when_quota_is_exhausted(self):
        cred = TenantAiCredential.objects.create(
            tenant=self.tenant_a,
            mode=TenantAiCredential.MODE_INCLUDED,
            monthly_request_limit=1,
            requests_this_month=1,
            period_month=timezone.now().strftime('%Y-%m'),
        )
        cred.save()
        self.assertIsNone(_resolve_provider(self.tenant_a))
        cred.requests_this_month = 0
        cred.save()
        self.assertEqual(_resolve_provider(self.tenant_a)['source'], 'included')

    @patch('apps.mcp_api.llm.requests.post')
    def test_chat_sends_tenant_key_to_provider(self, post_mock):
        post_mock.return_value.status_code = 200
        post_mock.return_value.json.return_value = {
            'choices': [{'message': {'content': 'Hola'}}]
        }
        cred = TenantAiCredential.objects.create(tenant=self.tenant_a)
        cred.set_api_key('clave-del-negocio-a')
        cred.save()

        text, _tools, _data = run_tool_chat(
            tenant=self.tenant_a,
            history=[],
            user_message='hola',
            tools=[],
            tool_map={},
        )
        self.assertEqual(text, 'Hola')
        self.assertEqual(post_mock.call_args.kwargs['headers']['Authorization'],
                         'Bearer clave-del-negocio-a')


class TenantAiCredentialApiTests(TestCase):
    """La vista se llama directamente: `force_authenticate` de APIClient se
    aplica después del TenantMiddleware, así que aquí se inyecta el tenant
    igual que lo haría el JWT en producción."""

    def setUp(self):
        self.user_a = UserFactory(role='Client-Admin')
        self.user_b = UserFactory(role='Client-Admin')
        self.factory = APIRequestFactory()

    def _call(self, user, method='get', data=None):
        request = getattr(self.factory, method)(
            '/api/mcp/ai-credential/', data or {}, format='json'
        )
        force_authenticate(request, user=user)
        request.tenant = user.tenant
        response = TenantAiCredentialView.as_view()(request)
        response.render()
        return response

    def test_save_and_read_never_exposes_the_key(self):
        resp = self._call(
            self.user_a, 'put',
            {'mode': 'byok', 'provider': 'gemini', 'api_key': 'clave-secreta-abcd'},
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertNotIn('clave-secreta-abcd', resp.content.decode())
        self.assertEqual(resp.data['key_hint'], '••••abcd')
        self.assertEqual(resp.data['source'], 'byok')

        resp = self._call(self.user_a)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('clave-secreta-abcd', resp.content.decode())
        self.assertNotIn('encrypted_api_key', resp.data)

    def test_tenants_are_isolated(self):
        self._call(
            self.user_a, 'put',
            {'mode': 'byok', 'provider': 'gemini', 'api_key': 'clave-del-negocio-a'},
        )
        resp = self._call(self.user_b)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['has_key'])
        self.assertNotEqual(self.user_a.tenant_id, self.user_b.tenant_id)

    def test_byok_requires_key_and_provider_is_validated(self):
        resp = self._call(self.user_a, 'put', {'mode': 'byok'})
        self.assertEqual(resp.status_code, 400)
        resp = self._call(
            self.user_a, 'put', {'mode': 'included', 'provider': 'desconocido'}
        )
        self.assertEqual(resp.status_code, 400)