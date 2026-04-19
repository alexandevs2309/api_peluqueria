from rest_framework import status
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from apps.tenants_api.models import Tenant
from apps.roles_api.models import Role, UserRole
from apps.settings_api.models import Branch, Setting
import uuid
import secrets
import string
import re
from datetime import datetime, time

User = get_user_model()
logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([AllowAny])
def check_email_availability(request):
    """
    Endpoint para verificar si un email está disponible para registro
    """
    email = request.GET.get('email', '').strip()

    if not email:
        return Response({
            'error': 'Email es requerido'
        }, status=status.HTTP_400_BAD_REQUEST)

    exists = User.objects.filter(email__iexact=email).exists()

    return Response({
        'available': not exists,
        'email': email
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_with_plan(request):
    """
    Endpoint para registro de nuevo cliente con plan
    """
    try:
        data = request.data
        logger.info("SaaS register_with_plan request received content_type=%s method=%s", request.content_type, request.method)

        required_fields = ['fullName', 'email', 'businessName', 'planType']
        missing_fields = []
        for field in required_fields:
            if not data.get(field):
                missing_fields.append(field)

        if missing_fields:
            logger.warning("SaaS register missing_fields=%s", missing_fields)
            return Response({
                'error': f'Campos requeridos faltantes: {", ".join(missing_fields)}',
                'missing_fields': missing_fields,
                'received_data': list(data.keys())
            }, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=data['email']).exists():
            return Response({
                'error': 'Ya existe un usuario con este email'
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription
            # 'trial' no es un plan real — mapear a 'basic' para onboarding
            plan_name = data['planType']
            if plan_name == 'trial':
                plan_name = 'basic'
            try:
                subscription_plan = SubscriptionPlan.objects.get(name=plan_name, is_active=True)
                logger.info("Subscription plan selected plan_id=%s", subscription_plan.id)
            except SubscriptionPlan.DoesNotExist:
                return Response({
                    'error': f'Plan no válido: {data["planType"]}'
                }, status=status.HTTP_400_BAD_REQUEST)

            password = generate_random_password()

            user = User(
                email=data['email'],
                full_name=data['fullName'],
                phone=data.get('phone', ''),
                is_active=True,
                is_superuser=True,
                is_staff=True,
                tenant=None,
                role=None
            )
            user.set_password(password)
            user.save(skip_validation=True)
            logger.info("Temporary user created user_id=%s", user.id)

            subdomain = generate_unique_subdomain(data['businessName'], user.id)
            tenant = Tenant.objects.create(
                name=data['businessName'],
                subdomain=subdomain,
                owner=user,
                contact_email=data['email'],
                contact_phone=data.get('phone', ''),
                address=data.get('address', ''),
                subscription_plan=subscription_plan,
                is_active=True
            )
            logger.info("Tenant created tenant_id=%s", tenant.id)

            user.is_superuser = False
            user.tenant = tenant
            user.role = 'Client-Admin'
            user.save(skip_validation=True)
            logger.info("User converted to Client-Admin user_id=%s tenant_id=%s", user.id, tenant.id)

            client_admin_role = Role.objects.filter(name='Client-Admin').first()
            if client_admin_role:
                UserRole.objects.get_or_create(
                    user=user,
                    role=client_admin_role,
                    tenant=tenant
                )

            trial_end = timezone.now() + timezone.timedelta(days=7)
            if tenant.trial_end_date:
                trial_end = timezone.make_aware(
                    datetime.combine(tenant.trial_end_date, time.max)
                )
            user_subscription = UserSubscription.objects.create(
                user=user,
                plan=subscription_plan,
                start_date=timezone.now(),
                end_date=trial_end,
                is_active=True,
                auto_renew=False
            )
            logger.info("Trial subscription created subscription_id=%s", user_subscription.id)

            from apps.billing_api.models import Invoice
            invoice = Invoice.objects.create(
                user=user,
                subscription=user_subscription,
                amount=subscription_plan.price,
                description=f"{subscription_plan.get_name_display()} - Primer mes",
                due_date=trial_end,
                status='pending'
            )
            logger.info("Initial invoice created invoice_id=%s", invoice.id)

            default_branch = Branch.objects.create(
                tenant=tenant,
                name='Sucursal Principal',
                address=data.get('address', 'Dirección por defecto'),
                is_main=True,
                is_active=True
            )
            logger.info("Default branch created branch_id=%s", default_branch.id)

            Setting.objects.create(
                branch=default_branch,
                business_name=tenant.name,
                business_email=tenant.contact_email,
                phone_number=tenant.contact_phone,
                address=tenant.address,
                currency='USD',
                timezone='America/Santo_Domingo'
            )
            logger.info("Default settings created for branch_id=%s", default_branch.id)

            # Crear categorías de servicios por defecto
            from apps.services_api.models import ServiceCategory
            default_categories = [
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
            ]
            for cat in default_categories:
                ServiceCategory.objects.get_or_create(
                    name=cat['name'],
                    tenant=tenant,
                    defaults={'description': cat['description']}
                )
            logger.info("Default service categories created for tenant_id=%s", tenant.id)

            # Crear categorías de productos por defecto
            from apps.inventory_api.models import ProductCategory
            default_product_categories = [
                {'name': 'Productos de Cabello', 'description': 'Shampoos, acondicionadores y tratamientos'},
                {'name': 'Productos de Barba', 'description': 'Aceites, bálsamos y ceras para barba'},
                {'name': 'Colorantes', 'description': 'Tintes y productos de coloración'},
                {'name': 'Herramientas de Corte', 'description': 'Tijeras, navajas y maquinillas'},
                {'name': 'Equipos Eléctricos', 'description': 'Secadores, planchas y rizadores'},
                {'name': 'Accesorios', 'description': 'Peines, cepillos y capas'},
                {'name': 'Higiene y Desinfección', 'description': 'Productos de limpieza y esterilización'},
                {'name': 'Retail', 'description': 'Productos para venta al cliente'},
            ]
            for cat in default_product_categories:
                ProductCategory.objects.get_or_create(
                    name=cat['name'],
                    tenant=tenant,
                    defaults={'description': cat['description']}
                )
            logger.info("Default product categories created for tenant_id=%s", tenant.id)

            send_welcome_email(user, password, tenant)

            response_data = {
                'success': True,
                'message': 'Cuenta creada exitosamente',
                'account': {
                    'business_name': data['businessName'],
                    'plan': data['planType'],
                    'user_id': user.id,
                    'subscription_status': 'trial',
                    'note': 'Configuración completando en segundo plano'
                },
                'credentials': {
                    'email': user.email,
                    'note': 'Credenciales enviadas por email'
                },
                'email_status': {
                    'email_sent': True,
                    'recipient': user.email,
                    'status': 'queued'
                }
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.exception("Error in register_with_plan")
        return Response({
            'error': f'Error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def generate_unique_subdomain(business_name, user_id):
    from apps.tenants_api.models import Tenant

    clean_name = re.sub(r'[^a-zA-Z0-9]', '', business_name.lower())
    clean_name = clean_name[:15]

    base_subdomain = f"{clean_name}{user_id}"
    if len(base_subdomain) > 50:
        base_subdomain = base_subdomain[:50]

    subdomain = base_subdomain
    counter = 1
    while Tenant.objects.filter(subdomain=subdomain).exists():
        suffix = str(counter)
        max_base_len = 50 - len(suffix)
        subdomain = f"{base_subdomain[:max_base_len]}{suffix}"
        counter += 1

    return subdomain


def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(characters) for _ in range(length))


def send_welcome_email(user, password, tenant):
    """Envía email de bienvenida real con credenciales"""
    from apps.auth_api.tasks import send_email_async
    from django.conf import settings as django_settings

    frontend_url = getattr(django_settings, 'FRONTEND_URL', 'http://localhost:4200')
    login_url = f"{frontend_url}/auth/login"

    subject = f"¡Bienvenido a BarberSaaS, {user.full_name}!"

    text_body = (
        f"Hola {user.full_name},\n\n"
        f"Tu cuenta ha sido creada exitosamente.\n\n"
        f"Barbería: {tenant.name}\n"
        f"Email: {user.email}\n"
        f"Contraseña temporal: {password}\n\n"
        f"Inicia sesión en: {login_url}\n\n"
        f"Por seguridad, cambia tu contraseña después de iniciar sesión.\n\n"
        f"El equipo de BarberSaaS"
    )

    html_body = f"""
    <div style="font-family:Arial,sans-serif;background:#f8fafc;padding:20px;">
      <div style="max-width:600px;margin:0 auto;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:24px;">
        <h2 style="color:#111827;">¡Bienvenido a BarberSaaS!</h2>
        <p>Hola <strong>{user.full_name}</strong>,</p>
        <p>Tu cuenta ha sido creada exitosamente.</p>
        <div style="background:#f3f4f6;border-radius:8px;padding:16px;margin:16px 0;">
          <p style="margin:4px 0;"><strong>Barbería:</strong> {tenant.name}</p>
          <p style="margin:4px 0;"><strong>Email:</strong> {user.email}</p>
          <p style="margin:4px 0;"><strong>Contraseña temporal:</strong> <code style="background:#e5e7eb;padding:2px 6px;border-radius:4px;">{password}</code></p>
        </div>
        <p style="margin:24px 0;">
          <a href="{login_url}" style="background:#2563eb;color:#fff;text-decoration:none;padding:10px 20px;border-radius:8px;display:inline-block;font-weight:600;">Iniciar Sesión</a>
        </p>
        <p style="color:#6b7280;font-size:13px;">Por seguridad, cambia tu contraseña después de iniciar sesión.</p>
      </div>
    </div>
    """

    logger.info("Sending welcome email to user_id=%s tenant_id=%s", user.id, tenant.id)
    send_email_async.delay(subject, text_body, 'onboarding@resend.dev', [user.email], html_message=html_body)

    return {'email_sent': True, 'recipient': user.email, 'status': 'queued'}
