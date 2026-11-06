"""Pruebas de seguridad Sprint 2: rotación de refresh token."""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.tenants_api.models import Tenant

User = get_user_model()


class RefreshTokenRotationTests(TestCase):
    def setUp(self):
        self.plan = None
        self.tenant_a = Tenant.objects.create(name='Tenant A', subdomain='ta-sec', is_active=True)
        self.tenant_b = Tenant.objects.create(name='Tenant B', subdomain='tb-sec', is_active=True)
        self.user = User.objects.create_user(
            email='sec@example.com', password='SecPass123!', full_name='Sec User',
            tenant=self.tenant_a, is_email_verified=True,
        )
        self.client = APIClient()
        login = self.client.post('/api/auth/cookie-login/', {
            'email': 'sec@example.com', 'password': 'SecPass123!',
        }, format='json')
        self.assertEqual(login.status_code, 200)
        self.refresh_cookie = login.cookies.get('refresh_token')
        self.assertIsNotNone(self.refresh_cookie)

    def test_refresh_rotates_and_blacklists_old_token(self):
        old_refresh = self.refresh_cookie.value

        first = self.client.post('/api/auth/cookie-refresh/', {}, format='json')
        self.assertEqual(first.status_code, 200)

        with self.assertRaises(Exception):
            RefreshToken(old_refresh).verify()

        client2 = APIClient()
        client2.cookies['refresh_token'] = old_refresh
        reused = client2.post('/api/auth/cookie-refresh/', {}, format='json')
        self.assertEqual(reused.status_code, 401)

    def test_logout_revokes_refresh(self):
        refresh = self.refresh_cookie.value
        out = self.client.post('/api/auth/cookie-logout/', {}, format='json')
        self.assertIn(out.status_code, (200, 204))

        client2 = APIClient()
        client2.cookies['refresh_token'] = refresh
        reused = client2.post('/api/auth/cookie-refresh/', {}, format='json')
        self.assertEqual(reused.status_code, 401)

    def test_tenant_id_claim_cannot_be_tampered(self):
        # Token legítimo del usuario en tenant A
        token = RefreshToken.for_user(self.user)
        token['tenant_id'] = self.tenant_b.id  # intento de cambio de tenant
        tampered = str(token)

        client = APIClient()
        client.cookies['refresh_token'] = tampered
        resp = client.post('/api/auth/cookie-refresh/', {}, format='json')
        # Debe rechazarse por mismatch de tenant
        self.assertEqual(resp.status_code, 401)

    def test_cookies_are_httponly(self):
        login = self.client.post('/api/auth/cookie-login/', {
            'email': 'sec@example.com', 'password': 'SecPass123!',
        }, format='json')
        self.assertTrue(login.cookies['access_token']['httponly'])
        self.assertTrue(login.cookies['refresh_token']['httponly'])

