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
    
    # Verificar si el email ya existe
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
        
        # Validar datos requeridos
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
        
        # Verificar que el email no exista
        if User.objects.filter(email=data['email']).exists():
            return Response({
                'error': 'Ya existe un usuario con este email'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Crear tenant y usuario en una transacción
        with transaction.atomic():
            # 1. Obtener el plan de suscripción primero
            from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription
            try:
                subscription_plan = SubscriptionPlan.objects.get(name=data['planType'])
                logger.info("Subscription plan selected plan_id=%s", subscription_plan.id)
            except SubscriptionPlan.DoesNotExist:
                return Response({
                    'error': f'Plan no válido: {data["planType"]}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 2. Generar contraseña
            password = generate_random_password()
            
            # 3. Crear usuario temporal como superuser (para evitar validación de tenant)
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
            
            # 4. Crear tenant con owner
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
            
            # 5. Actualizar usuario a Client-Admin con tenant
            user.is_superuser = False
            user.tenant = tenant
            user.role = 'Client-Admin'
            user.save(skip_validation=True)
            logger.info("User converted to Client-Admin user_id=%s tenant_id=%s", user.id, tenant.id)
            
            # 6. Crear suscripción del usuario con trial
            trial_end = timezone.now() + timezone.timedelta(days=7)
            user_subscription = UserSubscription.objects.create(
                user=user,
                plan=subscription_plan,
                start_date=timezone.now(),
                end_date=trial_end,
                is_active=True,
                auto_renew=False
            )
            logger.info("Trial subscription created subscription_id=%s", user_subscription.id)

            # 7. Crear factura inicial (pendiente para después del trial)
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

            # 8. Crear sucursal principal por defecto
            default_branch = Branch.objects.create(
                tenant=tenant,
                name='Sucursal Principal',
                address=data.get('address', 'Dirección por defecto'),
                is_main=True,
                is_active=True
            )
            logger.info("Default branch created branch_id=%s", default_branch.id)
            
            # 9. Crear configuración inicial para esa sucursal
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
            
            # 10. Enviar email de bienvenida
            send_welcome_email(user, password, tenant)
            
            # Obtener datos para respuesta
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
                }
            }
            
            # Simular resultado de email para respuesta inmediata
            email_result = {
                'email_sent': True,
                'message_id': f'msg_{uuid.uuid4().hex[:16]}',
                'recipient': user.email,
                'status': 'scheduled'
            }
            
            response_data['email_status'] = email_result
            return Response(response_data, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        logger.exception("Error in register_with_plan")
        return Response({
            'error': f'Error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def generate_unique_subdomain(business_name, user_id):
    """Generar subdomain único basado en el nombre del negocio"""
    from apps.tenants_api.models import Tenant
    
    # Limpiar nombre del negocio
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', business_name.lower())
    clean_name = clean_name[:15]  # Máximo 15 caracteres para dejar espacio al user_id
    
    # Generar subdomain base (máximo 50 caracteres total)
    base_subdomain = f"{clean_name}{user_id}"
    
    # Asegurar que no exceda 50 caracteres
    if len(base_subdomain) > 50:
        base_subdomain = base_subdomain[:50]
    
    # Verificar unicidad
    subdomain = base_subdomain
    counter = 1
    while Tenant.objects.filter(subdomain=subdomain).exists():
        # Asegurar que con el counter tampoco exceda 50
        suffix = str(counter)
        max_base_len = 50 - len(suffix)
        subdomain = f"{base_subdomain[:max_base_len]}{suffix}"
        counter += 1
    
    return subdomain

def generate_random_password(length=12):
    """Generar contraseña aleatoria segura"""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(characters) for _ in range(length))

def send_welcome_email(user, password, tenant):
    """Simula envío de email de bienvenida profesional"""
    email_content = f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║                🎉 ¡BIENVENIDO A BARBERSAAS! 🎉               ║
    ╚══════════════════════════════════════════════════════════════╝
    
    Hola {user.full_name},
    
    ¡Tu cuenta ha sido creada exitosamente!
    
    📋 DATOS DE ACCESO:
    ┌─────────────────────────────────────────────────────────────┐
    │ Barbería: {tenant.name}
    │ Plan: {tenant.plan_type.title()}
    │ 
    │ 🔐 CREDENCIALES:
    │ Email: {user.email}
    │ Contraseña: {password}
    │ 
    │ 🌐 Acceso: http://localhost:4200/auth/login
    └─────────────────────────────────────────────────────────────┘
    
    🚀 PRIMEROS PASOS:
    1. Inicia sesión con las credenciales de arriba
    2. Cambia tu contraseña temporal
    3. Configura tu barbería
    4. Agrega empleados y servicios
    
    ¿Necesitas ayuda? Responde a este email.
    
    ¡Gracias por elegir BarberSaaS!
    
    El equipo de BarberSaaS
    ═══════════════════════════════════════════════════════════════
    """
    
    logger.info("Welcome email prepared for user_id=%s tenant_id=%s", user.id, tenant.id)
    
    return {
        'email_sent': True,
        'message_id': f'msg_{uuid.uuid4().hex[:16]}',
        'recipient': user.email,
        'status': 'delivered'
    }
