from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from apps.tenants_api.models import Tenant
from apps.roles_api.models import Role, UserRole
from apps.roles_api.default_permissions import ensure_role_default_permissions
from apps.settings_api.models import Branch, Setting, SystemSettings
from apps.auth_api.onboarding import generate_email_verification_token

import logging
import re
import secrets
import uuid
from datetime import datetime, time

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Contrato de errores
# ---------------------------------------------------------------------------

def _error_response(request, code, message, http_status, details=None):
    """Respuesta de error controlada (nunca expone excepciones internas)."""
    trace_id = getattr(request, 'request_id', None) or uuid.uuid4().hex
    payload = {
        # ``error`` se mantiene por compatibilidad con clientes existentes.
        'error': message,
        'code': code,
        'type': 'VALIDATION' if http_status < 500 else 'SYSTEM',
        'message': message,
        'details': details or {},
        'timestamp': timezone.now().isoformat(),
        'trace_id': trace_id,
        'severity': 'WARNING' if http_status < 500 else 'ERROR',
        'origin': 'Registration',
    }
    return Response(payload, status=http_status)


# ---------------------------------------------------------------------------
# Validación del registro
# ---------------------------------------------------------------------------

class RegisterWithPlanSerializer(serializers.Serializer):
    """Valida el contrato camelCase que envía el frontend de signup."""

    fullName = serializers.CharField(max_length=255, trim_whitespace=True)
    email = serializers.EmailField(max_length=255)
    businessName = serializers.CharField(max_length=100, trim_whitespace=True)
    planType = serializers.CharField(max_length=100, trim_whitespace=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    address = serializers.CharField(required=False, allow_blank=True, default='')
    billingInterval = serializers.CharField(required=False, allow_blank=True)
    # Compatibilidad con clientes que envían snake_case (legacy/tests).
    billing_interval = serializers.CharField(required=False, allow_blank=True, write_only=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate_fullName(self, value):
        value = (value or '').strip()
        if len(value) < 2:
            raise serializers.ValidationError('El nombre completo debe tener al menos 2 caracteres.')
        return value

    def validate_businessName(self, value):
        value = (value or '').strip()
        if len(value) < 2:
            raise serializers.ValidationError('El nombre del negocio debe tener al menos 2 caracteres.')
        return value

    def validate_email(self, value):
        email = (value or '').strip().lower()
        try:
            validate_email(email)
        except DjangoValidationError:
            raise serializers.ValidationError('Ingresa un correo electrónico válido.')
        return email

    def validate_billingInterval(self, value):
        value = (value or 'month').strip().lower()
        return value if value in {'month', 'year'} else 'month'

    def validate(self, attrs):
        # Normaliza camelCase y snake_case a un único valor canónico.
        raw_interval = (
            attrs.get('billingInterval')
            or attrs.get('billing_interval')
            or 'month'
        )
        interval = (raw_interval or 'month').strip().lower()
        attrs['billingInterval'] = interval if interval in {'month', 'year'} else 'month'
        attrs.pop('billing_interval', None)
        return attrs

    def validate_password(self, value):
        if not value:
            return ''
        from apps.auth_api.serializers import validate_password_policy

        return validate_password_policy(value)


# ---------------------------------------------------------------------------
# Helpers de generación
# ---------------------------------------------------------------------------

def generate_unique_subdomain(business_name, user_id=None):
    """Genera un subdominio único y legible a partir del nombre del negocio.

    ``user_id`` se conserva en la firma por compatibilidad, pero ya no se usa:
    el usuario se crea después del tenant para respetar la restricción
    multi-tenant de la base de datos.
    """
    base = re.sub(r'[^a-z0-9]+', '-', (business_name or '').lower()).strip('-')
    base = base[:32] or 'negocio'

    for _ in range(20):
        suffix = secrets.token_hex(3)
        candidate = f'{base}-{suffix}'[:50]
        if not Tenant.objects.filter(subdomain=candidate).exists():
            return candidate

    # Fallback determinista ante una colisión improbable.
    counter = 1
    candidate = base
    while Tenant.objects.filter(subdomain=candidate).exists():
        candidate = f'{base[:40]}{counter}'
        counter += 1
    return candidate


def generate_unique_tenant_name(business_name):
    """Evita el 500 por ``Tenant.name`` duplicado sin bloquear el registro."""
    base = (business_name or '').strip()[:95] or 'Mi negocio'
    if not Tenant.objects.filter(name__iexact=base).exists():
        return base

    for index in range(2, 100):
        candidate = f'{base[:90]} ({index})'
        if not Tenant.objects.filter(name__iexact=candidate).exists():
            return candidate

    return f'{base[:80]} {secrets.token_hex(3)}'


def generate_random_password(length=12):
    import string

    characters = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(characters) for _ in range(length))


def _get_plan(plan_type):
    from apps.subscriptions_api.models import SubscriptionPlan

    return SubscriptionPlan.objects.filter(
        name=plan_type,
        is_active=True,
        is_public=True,
    ).first()


def _trial_end_datetime(tenant):
    if tenant.trial_end_date:
        return timezone.make_aware(datetime.combine(tenant.trial_end_date, time.max))
    trial_days = max(0, int(SystemSettings.get_settings().trial_days or 0))
    return timezone.now() + timezone.timedelta(days=trial_days)


def _dispatch_onboarding_email(user_id, tenant_id, set_password_url=None):
    """Re-fetch fuera de la transacción y envía el correo."""
    from apps.auth_api.onboarding import send_onboarding_email

    try:
        user = User.objects.filter(pk=user_id).first()
        tenant = Tenant.objects.filter(pk=tenant_id).first()
        if user and tenant:
            send_onboarding_email(user, tenant, set_password_url=set_password_url)
    except Exception:  # pragma: no cover - nunca debe romper la respuesta
        logger.exception('No se pudo encolar el correo de onboarding user_id=%s', user_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def check_email_availability(request):
    """Indica si un correo puede usarse para registrarse (case-insensitive)."""
    email = (request.GET.get('email') or '').strip().lower()

    if not email:
        return _error_response(
            request,
            'EMAIL_REQUIRED',
            'El correo electrónico es requerido.',
            status.HTTP_400_BAD_REQUEST,
        )

    try:
        validate_email(email)
    except DjangoValidationError:
        return _error_response(
            request,
            'INVALID_EMAIL',
            'Ingresa un correo electrónico válido.',
            status.HTTP_400_BAD_REQUEST,
        )

    cache_key = f'email_check:{email}'
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    exists = User.objects.filter(email__iexact=email).exists()
    data = {'available': not exists, 'email': email}
    cache.set(cache_key, data, 30)

    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_with_plan(request):
    """Registro transaccional de propietario + negocio + trial + factura.

    El orden respeta la restricción ``user_must_have_tenant_or_be_superuser``:
    se crea primero el tenant (sin owner), luego el usuario con su tenant y
    finalmente se asigna el owner. El correo se envía con ``on_commit`` y el
    enlace de contraseña es de un solo uso.
    """
    serializer = RegisterWithPlanSerializer(data=request.data)
    if not serializer.is_valid():
        first_error = next(iter(serializer.errors.values()))
        message = first_error[0] if isinstance(first_error, (list, tuple)) else str(first_error)
        return _error_response(
            request,
            'VALIDATION_ERROR',
            message,
            status.HTTP_400_BAD_REQUEST,
            details=serializer.errors,
        )

    data = serializer.validated_data
    email = data['email']
    logger.info('SaaS register_with_plan request email=%s plan=%s', email, data['planType'])

    # Validación de duplicado case-insensitive ANTES de abrir la transacción.
    if User.objects.filter(email__iexact=email).exists():
        return _error_response(
            request,
            'EMAIL_ALREADY_REGISTERED',
            'Ya existe una cuenta con este correo electrónico.',
            status.HTTP_409_CONFLICT,
            details={'email': ['Ya existe una cuenta con este correo electrónico.']},
        )

    subscription_plan = _get_plan(data['planType'])
    if subscription_plan is None:
        return _error_response(
            request,
            'INVALID_PLAN',
            'El plan seleccionado no está disponible.',
            status.HTTP_400_BAD_REQUEST,
            details={'planType': ['Plan inválido o no disponible.']},
        )

    provided_password = data.get('password') or ''
    billing_interval = data['billingInterval']

    try:
        with transaction.atomic():
            from decimal import Decimal

            from apps.billing_api.models import Invoice
            from apps.inventory_api.models import ProductCategory
            from apps.services_api.models import ServiceCategory
            from apps.subscriptions_api.models import UserSubscription

            # 1. Tenant primero (owner se asigna después de crear el usuario).
            tenant = Tenant.objects.create(
                name=generate_unique_tenant_name(data['businessName']),
                subdomain=generate_unique_subdomain(data['businessName']),
                owner=None,
                contact_email=email,
                contact_phone=data.get('phone') or '',
                address=data.get('address') or '',
                subscription_plan=subscription_plan,
                is_active=True,
            )
            logger.info('Tenant created tenant_id=%s', tenant.id)

            # 2. Usuario propietario, sin privilegios de staff/superusuario.
            user = User(
                email=email,
                full_name=data['fullName'],
                phone=data.get('phone') or None,
                is_active=True,
                is_email_verified=False,
                is_staff=False,
                is_superuser=False,
                tenant=tenant,
                role='Client-Admin',
                business_role='owner',
                email_verification_token=generate_email_verification_token(),
            )
            if provided_password:
                user.set_password(provided_password)
            else:
                # Sin contraseña usable hasta consumir el enlace de un solo uso.
                user.set_unusable_password()
            user.save()
            logger.info('Owner created user_id=%s tenant_id=%s', user.id, tenant.id)

            tenant.owner = user
            tenant.save(update_fields=['owner', 'updated_at'])

            # 3. Rol CLIENT_ADMIN garantizado (y sin privilegios globales).
            client_admin_role, _ = Role.objects.get_or_create(
                name='Client-Admin',
                defaults={'scope': 'TENANT', 'description': 'Administrador del negocio'},
            )
            ensure_role_default_permissions(client_admin_role)
            UserRole.objects.get_or_create(
                user=user,
                role=client_admin_role,
                tenant=tenant,
            )
            logger.info('Client-Admin role assigned user_id=%s tenant_id=%s', user.id, tenant.id)

            # 4. Suscripción de prueba.
            trial_end = _trial_end_datetime(tenant)
            user_subscription = UserSubscription.objects.create(
                user=user,
                plan=subscription_plan,
                start_date=timezone.now(),
                end_date=trial_end,
                is_active=True,
                auto_renew=False,
                billing_interval=billing_interval,
            )
            logger.info('Trial subscription created subscription_id=%s', user_subscription.id)

            # 5. Factura inicial (pendiente de pago al finalizar el trial).
            price_per_cycle = (
                subscription_plan.annual_price
                if billing_interval == 'year'
                else subscription_plan.price
            )
            if billing_interval == 'year' and not price_per_cycle:
                price_per_cycle = subscription_plan.price * 12 * Decimal('0.8')

            invoice = Invoice.objects.create(
                tenant=tenant,
                user=user,
                subscription=user_subscription,
                amount=price_per_cycle,
                description=(
                    f"{subscription_plan.get_name_display()} - Primer "
                    f"{'año' if billing_interval == 'year' else 'mes'}"
                ),
                due_date=trial_end,
                status='pending',
            )
            logger.info('Initial invoice created invoice_id=%s', invoice.id)

            # 6. Sucursal principal + configuración.
            default_branch = Branch.objects.create(
                tenant=tenant,
                name='Sucursal Principal',
                address=data.get('address') or 'Dirección por defecto',
                is_main=True,
                is_active=True,
            )
            Setting.objects.create(
                branch=default_branch,
                business_name=tenant.name,
                business_email=tenant.contact_email,
                phone_number=tenant.contact_phone,
                address=tenant.address,
                currency='USD',
                timezone='America/Santo_Domingo',
            )
            logger.info('Main branch and settings created branch_id=%s', default_branch.id)

            # 7. Catálogos por defecto.
            for cat in [
                {'name': 'Corte de Cabello', 'description': 'Servicios de corte de cabello'},
                {'name': 'Barba', 'description': 'Servicios de arreglo y diseño de barba'},
                {'name': 'Afeitado', 'description': 'Servicios de afeitado clásico'},
                {'name': 'Tratamientos', 'description': 'Tratamientos capilares y de cuero cabelludo'},
                {'name': 'Peinado', 'description': 'Servicios de peinado y estilizado'},
                {'name': 'Coloración', 'description': 'Tintes, mechas y coloración'},
                {'name': 'Keratina', 'description': 'Tratamientos de keratina y alisado'},
                {'name': 'Cejas', 'description': 'Diseño y depilación de cejas'},
                {'name': 'Masaje Capilar', 'description': 'Masajes de cuero cabelludo'},
                {'name': 'Extensiones', 'description': 'Colocación de extensiones de cabello'},
                {'name': 'Combo', 'description': 'Paquetes y servicios combinados'},
            ]:
                ServiceCategory.objects.get_or_create(
                    name=cat['name'],
                    tenant=tenant,
                    defaults={'description': cat['description']},
                )

            for cat in [
                {'name': 'Productos de Cabello', 'description': 'Shampoos, acondicionadores y tratamientos'},
                {'name': 'Productos de Barba', 'description': 'Aceites, bálsamos y ceras para barba'},
                {'name': 'Colorantes', 'description': 'Tintes y productos de coloración'},
                {'name': 'Herramientas de Corte', 'description': 'Tijeras, navajas y maquinillas'},
                {'name': 'Equipos Eléctricos', 'description': 'Secadores, planchas y rizadores'},
                {'name': 'Accesorios', 'description': 'Peines, cepillos y capas'},
                {'name': 'Higiene y Desinfección', 'description': 'Productos de limpieza y esterilización'},
                {'name': 'Retail', 'description': 'Productos para venta al cliente'},
            ]:
                ProductCategory.objects.get_or_create(
                    name=cat['name'],
                    tenant=tenant,
                    defaults={'description': cat['description']},
                )

            # 8. Enlaces y correo DESPUÉS del commit.
            set_password_url = None
            if not provided_password:
                from apps.auth_api.onboarding import build_set_password_url

                set_password_url = build_set_password_url(user, email=user.email)

            trial_days = max(0, int(SystemSettings.get_settings().trial_days or 0))
            response_data = {
                'success': True,
                'message': (
                    'Cuenta creada exitosamente. Revisa tu correo para verificar '
                    'tu cuenta y crear tu contraseña.'
                ),
                'account': {
                    'business_name': tenant.name,
                    'plan': subscription_plan.name,
                    'plan_display': subscription_plan.get_name_display(),
                    'user_id': user.id,
                    'subscription_status': tenant.subscription_status,
                    'trial_days': trial_days,
                    'trial_end_date': tenant.trial_end_date.isoformat() if tenant.trial_end_date else None,
                    'subdomain': tenant.subdomain,
                    'billing_interval': billing_interval,
                    'email': user.email,
                    'requires_email_verification': not user.is_email_verified,
                    'requires_password_setup': not user.has_usable_password(),
                },
                'email_status': {
                    'email_sent': True,
                    'recipient': user.email,
                    'status': 'queued',
                },
            }

            transaction.on_commit(
                lambda: _dispatch_onboarding_email(user.id, tenant.id, set_password_url)
            )

        return Response(response_data, status=status.HTTP_201_CREATED)

    except IntegrityError:
        # Carrera entre dos registros simultáneos (email/tenant duplicado).
        logger.warning('Registration integrity conflict email=%s', email)
        return _error_response(
            request,
            'EMAIL_ALREADY_REGISTERED',
            'Ya existe una cuenta con este correo electrónico.',
            status.HTTP_409_CONFLICT,
        )
    except Exception:
        # Nunca se expone str(e) ni stack traces al cliente.
        logger.exception('Error in register_with_plan email=%s', email)
        return _error_response(
            request,
            'REGISTRATION_FAILED',
            'No pudimos crear tu cuenta en este momento. Intenta nuevamente.',
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ---------------------------------------------------------------------------
# Compatibilidad con llamadas existentes
# ---------------------------------------------------------------------------

def send_welcome_email(user, password, tenant):  # noqa: ARG001 - firma legacy
    """Compatibilidad: el flujo actual usa enlaces de un solo uso."""
    from apps.auth_api.onboarding import send_onboarding_email

    return send_onboarding_email(user, tenant)
