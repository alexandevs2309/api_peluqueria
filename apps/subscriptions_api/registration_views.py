from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.tenants_api.models import Tenant
from apps.roles_api.models import Role, UserRole
from apps.settings_api.models import Branch, Setting
import uuid
import secrets
import string
import re

User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def register_with_plan(request):
    """
    Endpoint para registro de nuevo cliente con plan
    """
    try:
        data = request.data
        print(f"\n=== REGISTRO SaaS DEBUG ===")
        print(f"Datos recibidos: {data}")
        print(f"Content-Type: {request.content_type}")
        print(f"Method: {request.method}")
        print(f"Headers: {dict(request.headers)}")
        print(f"========================\n")
        
        # Validar datos requeridos
        required_fields = ['fullName', 'email', 'businessName', 'planType']
        missing_fields = []
        for field in required_fields:
            if not data.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            print(f"Campos faltantes: {missing_fields}")
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
            # 1. Crear usuario primero
            password = generate_random_password()
            print(f"Creando usuario: {data['email']}")
            user = User.objects.create(
                email=data['email'],
                full_name=data['fullName'],
                phone=data.get('phone', ''),
                is_active=True
            )
            user.set_password(password)
            user.save()
            print(f"Usuario creado: {user.id}")
            
            # 2. Obtener el plan de suscripción
            from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription
            try:
                subscription_plan = SubscriptionPlan.objects.get(name=data['planType'])
                print(f"Plan encontrado: {subscription_plan.name}")
            except SubscriptionPlan.DoesNotExist:
                return Response({
                    'error': f'Plan no válido: {data["planType"]}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 3. Crear tenant con plan
            subdomain = generate_unique_subdomain(data['businessName'], user.id)
            print(f"Creando tenant con subdomain: {subdomain}")
            tenant = Tenant.objects.create(
                name=data['businessName'],
                subdomain=subdomain,
                owner=user,
                contact_email=data['email'],
                contact_phone=data.get('phone', ''),
                subscription_plan=subscription_plan,  # ✅ Asignar plan objeto
                is_active=True
            )
            print(f"Tenant creado: {tenant.id} con plan: {tenant.plan_type}")
            
            # 4. Crear suscripción del usuario
            user_subscription = UserSubscription.objects.create(
                user=user,
                plan=subscription_plan,
                is_active=True,
                auto_renew=True
            )
            print(f"Suscripción creada: {user_subscription.id}")
            
            # 5. Asignar tenant al usuario
            user.tenant = tenant
            user.save()
            
            # 6. Asignar rol
            admin_role = Role.objects.get(name='Client-Admin')
            UserRole.objects.create(user=user, role=admin_role)
            print(f"Rol asignado")

            # 7. Crear sucursal principal por defecto
            default_branch = Branch.objects.create(
                tenant=tenant,
                name='Sucursal Principal',
                address=data.get('address', 'Dirección por defecto'),
                is_main=True,
                is_active=True
            )
            print(f"Sucursal creada correctamente: {default_branch.id}")
            
            # 8. Crear configuración inicial para esa sucursal
            Setting.objects.create(
                branch=default_branch,
                business_name=tenant.name,
                business_email=tenant.contact_email,
                phone_number=tenant.contact_phone,
                address=tenant.address,
                currency='USD',
                timezone='America/Santo_Domingo'
            )
            print(f'Configuración por defecto creada para sucursal: {default_branch.id}')


            # 9. Simular envío de email
            email_result = send_welcome_email(user, password, tenant)
            
            return Response({
                'success': True,
                'message': 'Cuenta creada exitosamente',
                'account': {
                    'business_name': tenant.name,
                    'plan': tenant.plan_type,
                    'tenant_id': tenant.id
                },
                'credentials': {
                    'email': user.email,
                    'note': 'Credenciales enviadas por email'
                },
                'email_status': email_result
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        print(f"Error en registro: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({
            'error': f'Error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def generate_unique_subdomain(business_name, user_id):
    """Generar subdomain único basado en el nombre del negocio"""
    from apps.tenants_api.models import Tenant
    
    # Limpiar nombre del negocio
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', business_name.lower())
    clean_name = clean_name[:20]  # Máximo 20 caracteres
    
    # Generar subdomain base
    base_subdomain = f"{clean_name}{user_id}"
    
    # Verificar unicidad
    subdomain = base_subdomain
    counter = 1
    while Tenant.objects.filter(subdomain=subdomain).exists():
        subdomain = f"{base_subdomain}{counter}"
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
    
    print("\n" + "="*60)
    print("📧 EMAIL ENVIADO A:", user.email)
    print("="*60)
    print(email_content)
    print("="*60 + "\n")
    
    return {
        'email_sent': True,
        'message_id': f'msg_{uuid.uuid4().hex[:16]}',
        'recipient': user.email,
        'status': 'delivered'
    }