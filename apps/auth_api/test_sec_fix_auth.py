"""Regresiones de seguridad: BE-09, BE-16, BE-17, CR-03, CR-04, CR-12 y CR-18."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auth_api.authentication import CookieJWTAuthentication
from apps.auth_api.cookie_views import CookieLoginView, CookieLogoutView, LookupSubdomainView
from apps.auth_api.middleware import CSRFProtectionMiddleware
from apps.auth_api.models import ActiveSession
from apps.auth_api.serializers import EmployeeUserSerializer
from apps.auth_api.views import RegisterView, VerifyAuthView, hash_token
from apps.subscriptions_api.models import SubscriptionPlan
from apps.tenants_api.models import Tenant

User = get_user_model()


def _make_tenant(suffix, plan_name='basic'):
    plan, _ = SubscriptionPlan.objects.get_or_create(
        name=plan_name,
        defaults={'price': 10, 'duration_month': 1, 'is_active': True, 'is_public': True},
    )
    return Tenant.objects.create(
        name=f'Tenant {suffix}',
        subdomain=f'sec-fix-{suffix}',
        subscription_plan=plan,
        subscription_status='active',
        is_active=True,
    )


def test_sec_fix_be09_csrf_enforced_without_debug_or_pytest_bypass():
    factory = RequestFactory = APIRequestFactory()
    middleware = CSRFProtectionMiddleware(lambda _r: None)
    view = lambda _r: None

    with override_settings(DEBUG=False):
        request = factory.post('/api/clients/clients/', {}, format='json')
        response = middleware.process_view(request, view, (), {})
        assert response.status_code == 403

        request = factory.post(
            '/api/clients/clients/', {}, format='json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert middleware.process_view(request, view, (), {}) is None

        # Las exenciones se limitan a callbacks externos y formularios públicos.
        webhook = factory.post('/api/billing/webhooks/stripe/', {}, format='json')
        assert middleware.process_view(webhook, view, (), {}) is None
        payments = factory.post('/api/payments/payments/', {}, format='json')
        assert middleware.process_view(payments, view, (), {}).status_code == 403


def test_sec_fix_be16_lookup_subdomain_rejects_foreign_origin():
    factory = APIRequestFactory()
    view = LookupSubdomainView.as_view()

    evil = factory.post(
        '/api/auth/lookup-subdomain/', {}, format='json',
        HTTP_ORIGIN='https://evil.example',
    )
    assert view(evil).status_code == 403

    same_origin = factory.post(
        '/api/auth/lookup-subdomain/', {}, format='json',
        HTTP_ORIGIN='http://testserver',
    )
    assert view(same_origin).status_code == 400  # email requerido, origen válido


def test_sec_fix_be17_plain_jwt_fallback_removed_from_defaults():
    authentication = settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']
    assert authentication == ['apps.auth_api.authentication.CookieJWTAuthentication']


def test_sec_fix_cr18_verify_auth_uses_cookie_jwt_authentication():
    assert VerifyAuthView.authentication_classes == [CookieJWTAuthentication]


@pytest.mark.django_db
def test_sec_fix_cr18_verify_auth_accepts_gateway_bearer_token():
    tenant = _make_tenant('verify')
    user = User.objects.create_user(
        email='verify@example.com', password='pass',
        full_name='Verify User', tenant=tenant,
    )
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    access['tenant_id'] = tenant.id

    request = APIRequestFactory().get(
        '/api/auth/verify/', HTTP_AUTHORIZATION=f'Bearer {access}',
    )
    seen_tenant = {}

    def capture_role(_user, tenant=None):
        seen_tenant['tenant'] = tenant
        return 'Client-Admin'

    with patch('apps.auth_api.views.get_effective_role_api', side_effect=capture_role):
        response = VerifyAuthView.as_view()(request)

    assert response.status_code == 200
    assert response.data['authenticated'] is True
    assert seen_tenant['tenant'].id == tenant.id


@pytest.mark.django_db
def test_sec_fix_cr03_cookie_login_returns_success_true():
    tenant = _make_tenant('cookie-login')
    User.objects.create_user(
        email='cookie-login@example.com', password='StrongPass123!',
        full_name='Cookie Login', tenant=tenant,
        is_email_verified=True,
    )

    request = APIRequestFactory().post('/api/auth/cookie-login/', {
        'email': 'cookie-login@example.com',
        'password': 'StrongPass123!',
    }, format='json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    response = CookieLoginView.as_view()(request)

    assert response.status_code == 200
    assert response.data['success'] is True


@pytest.mark.django_db
def test_sec_fix_cr04_logout_expires_session_stored_as_hash():
    tenant = _make_tenant('logout')
    user = User.objects.create_user(
        email='logout@example.com', password='pass',
        full_name='Logout User', tenant=tenant,
    )
    refresh = RefreshToken.for_user(user)
    raw_refresh = str(refresh)
    session = ActiveSession.objects.create(
        user=user,
        ip_address='127.0.0.1',
        user_agent='test-agent',
        token_jti='sec-fix-logout-jti',
        refresh_token=hash_token(raw_refresh),
        is_active=True,
        tenant=tenant,
    )

    request = APIRequestFactory().post('/api/auth/cookie-logout/', {}, format='json')
    request.COOKIES['refresh_token'] = raw_refresh

    response = CookieLogoutView.as_view()(request)

    assert response.status_code == 200
    session.refresh_from_db()
    assert session.is_active is False


@pytest.mark.django_db
def test_sec_fix_be12_email_validation_scoped_to_tenant():
    tenant_a = _make_tenant('email-a')
    tenant_b = _make_tenant('email-b')
    User.objects.create_user(
        email='duplicate@example.com', password='pass',
        full_name='Existing User', tenant=tenant_a,
    )
    factory = APIRequestFactory()
    payload = {
        'email': 'duplicate@example.com',
        'full_name': 'New User',
        'password': 'StrongPass123!',
    }

    request_b = factory.post('/api/employees/users/', {}, format='json')
    request_b.tenant = tenant_b
    serializer_b = EmployeeUserSerializer(context={'request': request_b})
    # La validación unificada es por tenant: este email no existe en tenant_b.
    assert serializer_b.validate_email('duplicate@example.com') == 'duplicate@example.com'

    request_a = factory.post('/api/employees/users/', {}, format='json')
    request_a.tenant = tenant_a
    serializer_a = EmployeeUserSerializer(context={'request': request_a})
    # El validador global de DRF (email unique=True) corre antes que validate_email;
    # se invoca directamente para comprobar que el mensaje es por tenant.
    with pytest.raises(Exception) as exc_info:
        serializer_a.validate_email('duplicate@example.com')
    assert 'mismo negocio' in str(exc_info.value)


@pytest.mark.django_db
def test_sec_fix_cr15_register_view_ignores_non_public_plan():
    public_plan, _ = SubscriptionPlan.objects.get_or_create(
        name='basic',
        defaults={'price': 10, 'duration_month': 1, 'is_active': True, 'is_public': True},
    )
    SubscriptionPlan.objects.get_or_create(
        name='enterprise',
        defaults={'price': 999, 'duration_month': 12, 'is_active': True, 'is_public': False},
    )
    owner = User.objects.create_superuser(
        email='cr15-owner@example.com', password='pass', full_name='Owner',
    )

    view = RegisterView()
    view.request = SimpleNamespace(data={'planType': 'enterprise'})
    serializer = Mock()
    serializer.validated_data = {
        'email': 'cr15-new@example.com',
        'full_name': 'New Owner',
    }
    serializer.save.return_value = owner

    with patch('apps.auth_api.views._deliver_user_email'):
        view.perform_create(serializer)

    tenant = Tenant.objects.get(subdomain='newowner')
    assert tenant.subscription_plan_id == public_plan.id
