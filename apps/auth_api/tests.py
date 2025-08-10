import pytest
from rest_framework.test import APIClient, APIRequestFactory
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from .factories import UserFactory
from .models import User, ActiveSession, LoginAudit, AccessLog
from rest_framework_simplejwt.tokens import RefreshToken
from .permissions import RolePermission
from .models import Role, UserRole
import pyotp


@pytest.fixture(autouse=True)
def mock_celery(monkeypatch):
    monkeypatch.setattr("apps.auth_api.tasks.send_email_async.delay", lambda *a, **kw: None)


@pytest.mark.django_db
def test_register_user():
    client = APIClient()
    data = {
        'email': 'test@example.com',
        'full_name': 'Test User',
        'phone': '1234567890',
        'password': 'testpassword123',
        'password2': 'testpassword123',
        'role': 'Client'
    }
    response = client.post(reverse('register'), data)
    assert response.status_code == 201
    user = User.objects.get(email='test@example.com')
    assert not user.is_email_verified
    assert user.email_verification_token


@pytest.mark.django_db
def test_verify_email():
    user = UserFactory(is_email_verified=False)
    user.email_verification_token = "test-token"
    user.save()
    client = APIClient()
    response = client.get(reverse('verify-email', args=[user.email_verification_token]))
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.is_email_verified
    assert user.email_verification_token is None


@pytest.mark.django_db
def test_login_user():
    user = UserFactory(is_email_verified=True)
    client = APIClient()
    response = client.post(reverse('login'), {'email': user.email, 'password': 'testpassword'})
    assert response.status_code == 200
    assert 'access_token' in response.cookies
    assert 'refresh_token' in response.cookies
    assert ActiveSession.objects.filter(user=user, is_active=True).exists()
    assert AccessLog.objects.filter(user=user, event_type='LOGIN').exists()
    assert LoginAudit.objects.filter(user=user, successful=True).exists()


@pytest.mark.django_db
def test_login_with_mfa():
    user = UserFactory(is_email_verified=True, mfa_enabled=True, mfa_secret=pyotp.random_base32())
    client = APIClient()
    response = client.post(reverse('login'), {'email': user.email, 'password': 'testpassword'})
    assert response.status_code == 200
    assert response.data['detail'] == "Se requiere verificación MFA."
    assert 'access_token' not in response.cookies

    code = pyotp.TOTP(user.mfa_secret).now()
    response = client.post(reverse('mfa-login-verify'), {'email': user.email, 'code': code})
    assert response.status_code == 200
    assert 'access_token' in response.cookies


@pytest.mark.django_db
def test_logout():
    user = UserFactory(is_email_verified=True)
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.cookies['refresh_token'] = str(refresh)
    client.cookies['access_token'] = str(refresh.access_token)
    client.force_authenticate(user)
    response = client.post(reverse('logout'))
    assert response.status_code == 200
    assert AccessLog.objects.filter(user=user, event_type='LOGOUT').exists()

@pytest.mark.django_db
def test_change_password():
    # Crear usuario con contraseña específica
    user = UserFactory(password='testpassword')
    # No necesitas user.save() porque el post_generation ya lo hace

    client = APIClient()

    # Debug: verificar que la contraseña está bien configurada
    print(">>> USER EMAIL:", user.email)
    print(">>> EMAIL VERIFIED:", user.is_email_verified)
    print(">>> PASSWORD CHECK:", user.check_password('testpassword'))

    # Login real
    login_response = client.post(reverse('login'), {
        'email': user.email,
        'password': 'testpassword'
    }, format='json')

    assert login_response.status_code == 200
    access_token = login_response.data['access']
    
    # Debug: verificar qué usuario está en el token
    print(">>> LOGIN RESPONSE:", login_response.data)

    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    
    # Debug: hacer una llamada para ver qué usuario está autenticado
    profile_response = client.get('/api/auth/profile/')  # ajusta esta URL según tu API
    print(">>> AUTHENTICATED USER:", profile_response.data if profile_response.status_code == 200 else "No profile endpoint")
    print(">>> CREATED USER ID:", user.id)

    # Cambiar contraseña
    response = client.put(reverse('change-password'), {
        'old_password': 'testpassword',
        'new_password': 'newpassword123',
        'new_password2': 'newpassword123'
    }, format='json')

    print(">>> RESPONSE:", response.status_code, response.data)

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password('newpassword123')



@pytest.mark.django_db
def test_password_reset():
    user = UserFactory(is_email_verified=True, password='testpassword')

    client = APIClient()

    # Solicitar el correo de recuperación
    response = client.post(reverse('password-reset'), {
        'email': user.email
    }, format='json')

    assert response.status_code == 200
    assert AccessLog.objects.filter(user=user, event_type='PASSWORD_RESET_REQUEST').exists()
    
    # Obtener el token y uid válidos
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    # Confirmar el reseteo
    confirm_response = client.post(reverse('password-reset-confirm'), {
        'uid': uid,
        'token': token,
        'new_password': 'newpassword123'
    }, format='json')

    assert confirm_response.status_code == 200
    user.refresh_from_db()
    assert user.check_password('newpassword123')

@pytest.mark.django_db
def test_active_sessions():
    user = UserFactory(is_email_verified=True)
    client = APIClient()
    client.force_authenticate(user)
    ActiveSession.objects.create(
        user=user,
        ip_address='127.0.0.1',
        user_agent='test-agent',
        token_jti='test-jti',
        refresh_token='test-refresh',
        is_active=True
    )
    response = client.get(reverse('active-sessions'))
    print("Response data:", response.data)  # Depuración
    assert response.status_code == 200
    assert isinstance(response.data, dict), f"Expected dict, got {type(response.data)}"
    assert 'results' in response.data, f"'results' not in response.data: {response.data}"
    assert response.data['count'] == 1
    assert len(response.data['results']) == 1
    assert response.data['results'][0]['user_agent'] == 'test-agent'
    log = AccessLog.objects.filter(user=user, event_type='ACTIVE_SESSIONS_VIEW').first()
    assert log is not None


@pytest.mark.django_db
def test_terminate_session():
    user = UserFactory(is_email_verified=True)
    client = APIClient()
    client.force_authenticate(user)
    session = ActiveSession.objects.create(
        user=user,
        ip_address='127.0.0.1',
        user_agent='test-agent',
        token_jti='test-jti',
        refresh_token='test-refresh',
        is_active=True
    )
    response = client.delete(reverse('terminate-session', args=['test-jti']))
    assert response.status_code == 200
    session.refresh_from_db()
    assert not session.is_active
    assert session.expired_at


@pytest.mark.django_db
def test_mfa_setup_and_verify():
    user = UserFactory(is_email_verified=True)
    client = APIClient()
    client.force_authenticate(user)
    response = client.post(reverse('mfa-setup'))
    assert response.status_code == 200
    assert 'qr_code' in response.data
    assert 'secret' in response.data

    user.refresh_from_db()
    code = pyotp.TOTP(user.mfa_secret).now()
    response = client.post(reverse('mfa-verify'), {'code': code})
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.mfa_enabled

@pytest.mark.django_db
def test_role_permission_denies_anonymous():
    factory = APIRequestFactory()
    request = factory.get('/')
    request.user = None
    perm = RolePermission()
    assert not perm.has_permission(request, None)

@pytest.mark.django_db
def test_role_permission_denies_user_without_role():
    user = User.objects.create_user(email="user@test.com", password="123456", full_name="User Test")
    factory = APIRequestFactory()
    request = factory.get('/')
    request.user = user
    perm = RolePermission()
    assert not perm.has_permission(request, None)

@pytest.mark.django_db
def test_role_permission_allows_user_with_allowed_role():
    user = User.objects.create_user(email="admin@test.com", password="123456", full_name="Admin Test")
    role, _ = Role.objects.get_or_create(name="Admin")
    UserRole.objects.create(user=user, role=role)

    factory = APIRequestFactory()
    request = factory.get('/')
    request.user = user
    perm = RolePermission()
    assert perm.has_permission(request, None)


@pytest.mark.django_db
def test_login_inactive_user():
    user = UserFactory(is_email_verified=True, is_active=False)
    client = APIClient()
    data = {"email": user.email, "password": "123456"}
    response = client.post(reverse("login"), data)
    assert response.status_code == 400
    # Ajustar para aceptar mensaje genérico de credenciales inválidas
    assert "credenciales inválidas" in str(response.data).lower() or "inactive" in str(response.data).lower()


@pytest.mark.django_db
def test_verify_email_invalid_token():
    client = APIClient()
    response = client.get(reverse('verify-email', args=["invalid-token"]))
    assert response.status_code == 400
    assert "Token inválido" in str(response.data)


@pytest.mark.django_db
def test_mfa_login_invalid_code():
    user = UserFactory(is_email_verified=True, mfa_enabled=True, mfa_secret=pyotp.random_base32())
    client = APIClient()
    response = client.post(reverse("mfa-login-verify"), {
        "email": user.email,
        "code": "000000"  # código inválido
    })
    assert response.status_code == 400
    assert "MFA inválido" in str(response.data)


@pytest.mark.django_db
def test_mfa_verify_invalid_code():
    user = UserFactory(is_email_verified=True)
    client = APIClient()
    client.force_authenticate(user)

    user.mfa_secret = pyotp.random_base32()
    user.save()

    response = client.post(reverse('mfa-verify'), {"code": "123456"})
    assert response.status_code == 400
    assert "inválido" in str(response.data).lower()


@pytest.mark.django_db
def test_terminate_session_not_found():
    user = UserFactory(is_email_verified=True)
    client = APIClient()
    client.force_authenticate(user)
    response = client.delete(reverse('terminate-session', args=["no-existe-jti"]))
    assert response.status_code == 404
