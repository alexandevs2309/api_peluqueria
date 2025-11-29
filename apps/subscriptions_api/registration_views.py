from rest_framework import status
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
            # 1. Obtener el plan de suscripción primero
            from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription
            try:
                subscription_plan = SubscriptionPlan.objects.get(name=data['planType'])
                print(f"Plan encontrado: {subscription_plan.name}")
            except SubscriptionPlan.DoesNotExist:
                return Response({
                    'error': f'Plan no válido: {data["planType"]}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 2. Crear usuario SIN rol ni tenant inicialmente
            password = generate_random_password()
            print(f"Generando contraseña aleatoria: {password}")
            
            print(f"Creando usuario: {data['email']}")
            
            # Crear usuario básico sin rol ni tenant
            user = User.objects.create_user(
                email=data['email'],
                password=password,
                full_name=data['fullName'],
                phone=data.get('phone', ''),
                is_active=True
                # NO asignar role ni tenant aquí
            )
            print(f"Usuario creado: {user.id}")
            
            # 3. Programar creación de tenant, rol y suscripción después del commit
            def create_tenant_and_subscription():
                try:
                    # Crear tenant
                    subdomain = generate_unique_subdomain(data['businessName'], user.id)
                    print(f"Creando tenant con subdomain: {subdomain}")
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
                    print(f"Tenant creado: {tenant.id}")
                    
                    # Asignar tenant y rol al usuario
                    User.objects.filter(id=user.id).update(
                        tenant=tenant,
                        role='Client-Admin'
                    )
                    print(f"Usuario actualizado con tenant y rol Client-Admin")
                    
                    # Crear suscripción del usuario con trial
                    trial_end = timezone.now() + timezone.timedelta(days=7)
                    user_subscription = UserSubscription.objects.create(
                        user=user,
                        plan=subscription_plan,
                        start_date=timezone.now(),
                        end_date=trial_end,
                        is_active=True,
                        auto_renew=False
                    )
                    print(f"Suscripción trial creada: {user_subscription.id} hasta {trial_end}")

                    # Crear sucursal principal por defecto
                    default_branch = Branch.objects.create(
                        tenant=tenant,
                        name='Sucursal Principal',
                        address=data.get('address', 'Dirección por defecto'),
                        is_main=True,
                        is_active=True
                    )
                    print(f"Sucursal creada correctamente: {default_branch.id}")
                    
                    # Crear configuración inicial para esa sucursal
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
                    
                    # Enviar email de bienvenida
                    send_welcome_email(user, password, tenant)
                    
                except Exception as e:
                    print(f"Error en post-commit setup: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            # Programar ejecución después del commit
            transaction.on_commit(create_tenant_and_subscription)
            
            # Obtener datos para respuesta (tenant se creará después del commit)
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