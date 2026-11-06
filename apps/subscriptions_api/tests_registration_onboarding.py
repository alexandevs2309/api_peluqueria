"""Pruebas del registro/onboarding de AURON Suite (Sprint 1).

Cubren: registro exitoso, correo duplicado, creación de tenant, rol/permisos,
sucursal, trial, factura, verificación de correo, contraseña de un solo uso,
login posterior y aislamiento entre tenants.
"""
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from apps.auth_api.models import User
from apps.billing_api.models import Invoice
from apps.roles_api.models import Role, UserRole
from apps.settings_api.models import Branch
from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription
from apps.tenants_api.models import Tenant

pytestmark = pytest.mark.django_db

REGISTER_URL = '/api/subscriptions/register/'
SET_PASSWORD_URL = '/api/auth/set-password/'
LOGIN_URL = '/api/auth/login/'
BRANCHES_URL = '/api/settings/branches/'


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
        'fullName': 'Ana Pérez',
        'email': 'ana.perez@example.com',
        'businessName': 'Salón Aurora',
        'phone': '809-555-0100',
        'address': 'Av. Principal 123',
        'planType': 'standard',
        'billingInterval': 'month',
    }
    data.update(overrides)
    return data


def _register(api_client, **overrides):
    with patch('apps.subscriptions_api.registration_views._dispatch_onboarding_email') as dispatch:
        with TestCase.captureOnCommitCallbacks(execute=True):
            response = api_client.post(REGISTER_URL, _payload(**overrides), format='json')
    return response, dispatch


# ---------------------------------------------------------------------------
# Registro exitoso y provisioning
# ---------------------------------------------------------------------------

def test_successful_registration_provisions_everything(api_client, plan):
    response, dispatch = _register(api_client)

    assert response.status_code == 201, response.data
    assert response.data['success'] is True

    user = User.objects.get(email='ana.perez@example.com')
    tenant = Tenant.objects.get(owner=user)

    # Cuenta de propietario sin privilegios globales.
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.is_active is True
    assert user.is_email_verified is False
    assert user.email_verification_token
    assert user.has_usable_password() is False
    assert user.tenant_id == tenant.id
    assert user.role == 'Client-Admin'

    # Tenant + trial.
    assert tenant.name == 'Salón Aurora'
    assert tenant.subscription_plan_id == plan.id
    assert tenant.subscription_status == 'trial'
    assert tenant.trial_end_date is not None
    assert tenant.is_active is True

    # Rol CLIENT_ADMIN y permisos por tenant.
    user_role = UserRole.objects.get(user=user, tenant=tenant)
    assert user_role.role.name == 'Client-Admin'
    assert user_role.role.scope == 'TENANT'
    assert user_role.role.permissions.count() > 0

    # Sucursal principal.
    branches = Branch.objects.filter(tenant=tenant)
    assert branches.count() == 1
    assert branches.first().is_main is True

    # Suscripción de prueba.
    subscription = UserSubscription.objects.get(user=user)
    assert subscription.plan_id == plan.id
    assert subscription.is_active is True
    assert subscription.billing_interval == 'month'

    # Factura inicial pendiente.
    invoice = Invoice.objects.get(user=user)
    assert invoice.tenant_id == tenant.id
    assert invoice.status == 'pending'
    assert invoice.amount == plan.price
    assert invoice.due_date is not None

    # El correo se envía después del commit y con enlace de contraseña.
    dispatch.assert_called_once()
    args = dispatch.call_args.args
    assert args[0] == user.id
    assert args[1] == tenant.id
    assert args[2], 'Debe generarse un enlace de establecimiento de contraseña'


def test_registration_does_not_leak_internal_errors(api_client, plan):
    with patch.object(Tenant.objects, 'create', side_effect=RuntimeError('secret-internal-detail')):
        response = api_client.post(REGISTER_URL, _payload(), format='json')

    assert response.status_code == 500
    assert response.data['code'] == 'REGISTRATION_FAILED'
    assert 'secret-internal-detail' not in str(response.data)
    assert Tenant.objects.filter(name='Salón Aurora').exists() is False
    assert User.objects.filter(email='ana.perez@example.com').exists() is False


# ---------------------------------------------------------------------------
# Validaciones y duplicados
# ---------------------------------------------------------------------------

def test_duplicate_email_is_case_insensitive(api_client, plan):
    response, _ = _register(api_client)
    assert response.status_code == 201

    tenants_before = Tenant.objects.count()
    duplicate, _ = _register(api_client, email='ANA.PEREZ@Example.com', businessName='Otro Salón')

    assert duplicate.status_code == 409
    assert duplicate.data['code'] == 'EMAIL_ALREADY_REGISTERED'
    assert Tenant.objects.count() == tenants_before


def test_invalid_email_returns_controlled_validation_error(api_client, plan):
    response, _ = _register(api_client, email='no-es-un-email')

    assert response.status_code == 400
    assert response.data['code'] == 'VALIDATION_ERROR'
    assert 'email' in response.data['details']


def test_invalid_plan_returns_controlled_error(api_client, plan):
    response, _ = _register(api_client, planType='inexistente')

    assert response.status_code == 400
    assert response.data['code'] == 'INVALID_PLAN'
    assert User.objects.filter(email='ana.perez@example.com').exists() is False


def test_check_email_availability_is_case_insensitive(api_client, plan):
    user = User.objects.create_superuser(
        email='ocupado@example.com',
        password='pass',
        full_name='Ocupado',
    )
    response = api_client.get('/api/subscriptions/check-email/', {'email': 'OCUPADO@example.com'})

    assert response.status_code == 200
    assert response.data['available'] is False
    assert response.data['email'] == 'ocupado@example.com'
    assert user.pk


# ---------------------------------------------------------------------------
# Contraseña inicial de un solo uso
# ---------------------------------------------------------------------------

def test_initial_password_link_is_single_use(api_client, plan):
    response, _ = _register(api_client)
    assert response.status_code == 201

    user = User.objects.get(email='ana.perez@example.com')
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    # Validación previa al mostrar el formulario.
    validate = api_client.get(SET_PASSWORD_URL, {'uid': uid, 'token': token})
    assert validate.status_code == 200
    assert validate.data['valid'] is True
    assert validate.data['email'] == user.email

    # Establecer contraseña: verifica el correo y consume el token.
    created = api_client.post(
        SET_PASSWORD_URL,
        {'uid': uid, 'token': token, 'new_password': 'ClaveSegura123!'},
        format='json',
    )
    assert created.status_code == 200, created.data

    user.refresh_from_db()
    assert user.has_usable_password() is True
    assert user.check_password('ClaveSegura123!') is True
    assert user.is_email_verified is True
    assert user.email_verification_token is None

    # Segundo uso del mismo enlace: rechazado.
    reused = api_client.post(
        SET_PASSWORD_URL,
        {'uid': uid, 'token': token, 'new_password': 'OtraClave123!'},
        format='json',
    )
    assert reused.status_code == 400
    assert reused.data['code'] == 'INVALID_PASSWORD_OR_TOKEN'

    # Login posterior al registro.
    login = api_client.post(
        LOGIN_URL,
        {'email': 'ana.perez@example.com', 'password': 'ClaveSegura123!'},
        format='json',
    )
    assert login.status_code == 200, login.data
    assert login.data['user']['email'] == 'ana.perez@example.com'


def test_initial_password_rejects_invalid_token(api_client, plan):
    response = api_client.post(
        SET_PASSWORD_URL,
        {'uid': 'abc', 'token': 'invalido', 'new_password': 'ClaveSegura123!'},
        format='json',
    )
    assert response.status_code == 400
    assert response.data['code'] == 'INVALID_PASSWORD_OR_TOKEN'


# ---------------------------------------------------------------------------
# Verificación de correo
# ---------------------------------------------------------------------------

def test_email_verification_token_works_once(api_client, plan):
    response, _ = _register(api_client)
    assert response.status_code == 201

    user = User.objects.get(email='ana.perez@example.com')
    token = user.email_verification_token

    verified = api_client.get(f'/api/auth/verify-email/{token}/')
    assert verified.status_code == 200
    assert verified.data['email_verified'] is True

    user.refresh_from_db()
    assert user.is_email_verified is True
    assert user.email_verification_token is None

    reused = api_client.get(f'/api/auth/verify-email/{token}/')
    assert reused.status_code == 400
    assert reused.data['code'] == 'INVALID_VERIFICATION_TOKEN'


# ---------------------------------------------------------------------------
# Aislamiento entre tenants
# ---------------------------------------------------------------------------

def test_tenant_isolation_between_registered_businesses(api_client, plan):
    first, _ = _register(api_client)
    second, _ = _register(
        api_client,
        email='beto@example.com',
        businessName='Barbería Beta',
        phone='809-555-0200',
    )
    assert first.status_code == 201
    assert second.status_code == 201

    user_a = User.objects.get(email='ana.perez@example.com')
    user_b = User.objects.get(email='beto@example.com')

    assert user_a.tenant_id != user_b.tenant_id
    assert Branch.objects.filter(tenant=user_a.tenant).count() == 1
    assert Branch.objects.filter(tenant=user_b.tenant).count() == 1
    assert Invoice.objects.filter(tenant=user_a.tenant).count() == 1
    assert Invoice.objects.filter(tenant=user_b.tenant).count() == 1
    assert UserRole.objects.get(user=user_a).tenant_id == user_a.tenant_id
    assert UserRole.objects.get(user=user_b).tenant_id == user_b.tenant_id

    # El endpoint de sucursales solo expone la sucursal del tenant autenticado.
    client_a = APIClient()
    client_a.force_authenticate(user=user_a)
    listed = client_a.get(BRANCHES_URL)

    assert listed.status_code == 200, listed.data
    returned_ids = {item['id'] for item in listed.data}
    branch_a = Branch.objects.get(tenant=user_a.tenant)
    branch_b = Branch.objects.get(tenant=user_b.tenant)
    assert returned_ids == {branch_a.id}
    assert branch_b.id not in returned_ids
