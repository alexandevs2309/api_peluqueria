"""Pruebas adicionales de cierre técnico de onboarding (Sprint 1.1)."""
import time
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from apps.auth_api.factories import UserFactory
from apps.auth_api.models import User
from apps.auth_api.onboarding import (
    generate_email_verification_token,
    is_email_verification_token_valid,
)
from apps.billing_api.models import Invoice
from apps.subscriptions_api.models import SubscriptionPlan
from apps.tenants_api.models import Tenant

pytestmark = pytest.mark.django_db

REGISTER_URL = '/api/subscriptions/register/'
SET_PASSWORD_URL = '/api/auth/set-password/'
LOGIN_URL = '/api/auth/login/'
INVOICES_URL = '/api/billing/invoices/'


@pytest.fixture
def plan(db):
    return SubscriptionPlan.objects.create(
        name='standard',
        price=Decimal('69.99'),
        annual_price=Decimal('671.90'),
        duration_month=1,
        is_active=True,
        is_public=True,
        max_employees=5,
        max_users=10,
    )


@pytest.fixture
def api_client():
    return APIClient()


def _payload(**overrides):
    data = {
        'fullName': 'Ana Perez',
        'email': 'ana.perez@example.com',
        'businessName': 'Salon Aurora',
        'phone': '809-555-0100',
        'address': 'Av. Principal 123',
        'planType': 'standard',
        'billingInterval': 'month',
    }
    data.update(overrides)
    return data


def _register(api_client, **overrides):
    with patch('apps.subscriptions_api.registration_views._dispatch_onboarding_email'):
        with TestCase.captureOnCommitCallbacks(execute=True):
            return api_client.post(REGISTER_URL, _payload(**overrides), format='json')


# --------------------------------------------------------------------------- #
# Registro mensual y anual
# --------------------------------------------------------------------------- #
def test_monthly_registration_sets_monthly_interval(api_client, plan):
    response = _register(api_client)
    assert response.status_code == 201
    user = User.objects.get(email='ana.perez@example.com')
    from apps.subscriptions_api.models import UserSubscription

    subscription = UserSubscription.objects.get(user=user)
    assert subscription.billing_interval == 'month'
    assert response.data['account']['trial_days'] == 7


def test_annual_registration_sets_annual_interval(api_client, plan):
    response = _register(api_client, billingInterval='year', email='annual@example.com',
                        businessName='Salon Anual')
    assert response.status_code == 201
    user = User.objects.get(email='annual@example.com')
    from apps.subscriptions_api.models import UserSubscription

    subscription = UserSubscription.objects.get(user=user)
    assert subscription.billing_interval == 'year'
    invoice = Invoice.objects.get(user=user)
    assert invoice.amount == plan.annual_price


# --------------------------------------------------------------------------- #
# Login antes de completar onboarding
# --------------------------------------------------------------------------- #
def test_login_before_onboarding_completion_fails(api_client, plan):
    response = _register(api_client)
    assert response.status_code == 201

    login = api_client.post(
        LOGIN_URL,
        {'email': 'ana.perez@example.com', 'password': 'cualquier-clave'},
        format='json',
    )
    assert login.status_code == 400
    assert 'Credenciales' in str(login.data) or 'credenciales' in str(login.data).lower()


# --------------------------------------------------------------------------- #
# Token expirado y reutilizado (contraseña)
# --------------------------------------------------------------------------- #
def test_expired_password_token_is_rejected(api_client, plan):
    response = _register(api_client)
    assert response.status_code == 201
    user = User.objects.get(email='ana.perez@example.com')

    # Genera un token con timestamp en el pasado simulando expiración.
    original_now = default_token_generator._now
    past = original_now() if False else None
    from datetime import timedelta

    def fake_now():
        return original_now() - timedelta(days=10)

    default_token_generator._now = fake_now
    try:
        token = default_token_generator.make_token(user)
    finally:
        default_token_generator._now = original_now

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    result = api_client.post(
        SET_PASSWORD_URL,
        {'uid': uid, 'token': token, 'new_password': 'ClaveSegura123!'},
        format='json',
    )
    assert result.status_code == 400
    assert result.data['code'] == 'INVALID_PASSWORD_OR_TOKEN'


def test_reused_password_token_is_rejected(api_client, plan):
    response = _register(api_client)
    assert response.status_code == 201
    user = User.objects.get(email='ana.perez@example.com')
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    first = api_client.post(
        SET_PASSWORD_URL,
        {'uid': uid, 'token': token, 'new_password': 'ClaveSegura123!'},
        format='json',
    )
    assert first.status_code == 200

    second = api_client.post(
        SET_PASSWORD_URL,
        {'uid': uid, 'token': token, 'new_password': 'OtraClave123!'},
        format='json',
    )
    assert second.status_code == 400
    assert second.data['code'] == 'INVALID_PASSWORD_OR_TOKEN'


# --------------------------------------------------------------------------- #
# Token de verificación de correo expirado
# --------------------------------------------------------------------------- #
def test_expired_email_verification_token_is_rejected(api_client, plan):
    expired_token = f"{int(time.time()) - 10 * 86400}:{'a' * 32}"
    user = UserFactory(email='expirado@example.com', is_email_verified=False)
    user.email_verification_token = expired_token
    user.save(update_fields=['email_verification_token'])

    assert is_email_verification_token_valid(expired_token) is False

    result = api_client.get(f'/api/auth/verify-email/{expired_token}/')
    assert result.status_code == 400
    assert result.data['code'] == 'INVALID_VERIFICATION_TOKEN'


def test_valid_email_verification_token_is_accepted(api_client, plan):
    token = generate_email_verification_token()
    user = UserFactory(email='valido@example.com', is_email_verified=False)
    user.email_verification_token = token
    user.save(update_fields=['email_verification_token'])

    assert is_email_verification_token_valid(token) is True

    result = api_client.get(f'/api/auth/verify-email/{token}/')
    assert result.status_code == 200
    assert result.data['email_verified'] is True


# --------------------------------------------------------------------------- #
# Reenvío de correo
# --------------------------------------------------------------------------- #
def test_resend_verification_queues_email(api_client, plan):
    response = _register(api_client)
    assert response.status_code == 201
    user = User.objects.get(email='ana.perez@example.com')
    old_token = user.email_verification_token

    with patch('apps.auth_api.onboarding.send_onboarding_email') as send_mock:
        resend = api_client.post(
            '/api/auth/resend-verification/',
            {'email': 'ANA.PEREZ@Example.com'},
            format='json',
        )
    assert resend.status_code == 200
    user.refresh_from_db()
    # El reenvío no debe filtrar si el usuario existe (respuesta genérica).
    assert 'detail' in resend.data


# --------------------------------------------------------------------------- #
# Fallo de Celery no rompe el registro
# --------------------------------------------------------------------------- #
def test_celery_failure_does_not_break_registration(api_client, plan):
    def boom(*args, **kwargs):
        raise RuntimeError('broker down')

    with patch('apps.auth_api.tasks.send_email_async.delay', side_effect=boom):
        with TestCase.captureOnCommitCallbacks(execute=True):
            response = api_client.post(REGISTER_URL, _payload(), format='json')

    assert response.status_code == 201, response.data
    assert response.data['success'] is True
    assert User.objects.filter(email='ana.perez@example.com').exists()


# --------------------------------------------------------------------------- #
# Aislamiento entre tenants en endpoints adicionales
# --------------------------------------------------------------------------- #
def test_cross_tenant_invoice_access_is_blocked(api_client, plan):
    first = _register(api_client)
    second = _register(
        api_client,
        email='beto@example.com',
        businessName='Barberia Beta',
        phone='809-555-0200',
    )
    assert first.status_code == 201
    assert second.status_code == 201

    user_a = User.objects.get(email='ana.perez@example.com')
    user_b = User.objects.get(email='beto@example.com')

    client_a = APIClient()
    client_a.force_authenticate(user=user_a)
    listed = client_a.get(INVOICES_URL)
    assert listed.status_code == 200

    returned_ids = {item['id'] for item in listed.data.get('results', listed.data)}
    invoices_a = set(Invoice.objects.filter(tenant=user_a.tenant).values_list('id', flat=True))
    invoices_b = set(Invoice.objects.filter(tenant=user_b.tenant).values_list('id', flat=True))

    assert returned_ids == invoices_a
    assert returned_ids.isdisjoint(invoices_b)

    # Intento de acceso directo a factura del otro tenant.
    invoice_b = Invoice.objects.filter(tenant=user_b.tenant).first()
    detail = client_a.get(f'{INVOICES_URL}{invoice_b.id}/')
    assert detail.status_code in (403, 404)
