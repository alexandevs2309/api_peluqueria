import os
import django
from decimal import Decimal
from datetime import datetime, timedelta
import random
import sys

# Asegurar que el directorio raíz de Django esté en el path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Inicializar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription
from apps.settings_api.models import Branch, Setting
from apps.roles_api.models import Role, UserRole
from apps.roles_api.default_permissions import ensure_role_default_permissions
from apps.employees_api.models import Employee, WorkSchedule
from apps.services_api.models import ServiceCategory, Service, ServiceEmployee
from apps.inventory_api.models import ProductCategory, Supplier, Product, StockMovement
from apps.clients_api.models import Client
from apps.appointments_api.models import Appointment
from apps.pos_api.models import Sale, SaleDetail, Payment, CashRegister, PosConfiguration
from apps.billing_api.models import Invoice

User = get_user_model()

def seed_data():
    print("🌱 Iniciando población de 10 negocios realistas para desarrollo local...")

    # Obtener roles
    client_admin_role = Role.objects.get(name='Client-Admin')
    estilista_role = Role.objects.get(name='Estilista')
    cajera_role = Role.objects.get(name='Cajera')
    ensure_role_default_permissions(client_admin_role)
    ensure_role_default_permissions(estilista_role)
    ensure_role_default_permissions(cajera_role)

    # 10 Inquilinos (Tenants) de prueba realistas
    tenants_data = [
        {
            "name": "Barbería y Spa El Elegante",
            "subdomain": "elegante",
            "admin_email": "alexander.delrosario@auronsuite.com",
            "admin_name": "Alexander Del Rosario",
            "plan_name": "standard",
            "status": "active",
            "phone": "8095551234",
            "address": "Av. Gustavo Mejía Ricart 45, Ensanche Naco, Santo Domingo",
            "currency": "DOP",
            "poblar_detalles": True
        },
        {
            "name": "Estudio de Belleza V&M",
            "subdomain": "vmstudio",
            "admin_email": "valentina.medina@auronsuite.com",
            "admin_name": "Valentina Medina",
            "plan_name": "premium",
            "status": "active",
            "phone": "8095559876",
            "address": "Av. Winston Churchill, Bella Vista, Santo Domingo",
            "currency": "DOP",
            "poblar_detalles": True
        },
        {
            "name": "D'Carlos Barber Shop",
            "subdomain": "dcarlos",
            "admin_email": "carlos.mendez@auronsuite.com",
            "admin_name": "Carlos Méndez",
            "plan_name": "basic",
            "status": "trial",
            "phone": "8095551122",
            "address": "Calle Del Sol 12, Santiago de los Caballeros",
            "currency": "DOP",
            "poblar_detalles": False
        },
        {
            "name": "Senses Spa & Wellness",
            "subdomain": "senses",
            "admin_email": "laura.santos@auronsuite.com",
            "admin_name": "Laura Santos",
            "plan_name": "premium",
            "status": "active",
            "phone": "8295553344",
            "address": "Boulevard Turístico del Este, Punta Cana",
            "currency": "USD",
            "poblar_detalles": False
        },
        {
            "name": "Salón Miradas Express",
            "subdomain": "miradas",
            "admin_email": "clara.guzman@auronsuite.com",
            "admin_name": "Clara Guzmán",
            "plan_name": "standard",
            "status": "expired",
            "phone": "8095555566",
            "address": "Av. Libertad 88, San Francisco de Macorís",
            "currency": "DOP",
            "poblar_detalles": False
        },
        {
            "name": "The Gentleman's Club",
            "subdomain": "gentleman",
            "admin_email": "roberto.alvarez@auronsuite.com",
            "admin_name": "Roberto Álvarez",
            "plan_name": "enterprise",
            "status": "active",
            "phone": "8095559900",
            "address": "Av. Santa Rosa, La Romana",
            "currency": "DOP",
            "poblar_detalles": True
        },
        {
            "name": "Glow Hair & Nails",
            "subdomain": "glow",
            "admin_email": "patricia.reyes@auronsuite.com",
            "admin_name": "Patricia Reyes",
            "plan_name": "standard",
            "status": "trial",
            "phone": "8295552233",
            "address": "Calle Principal, Las Terrenas, Samaná",
            "currency": "USD",
            "poblar_detalles": False
        },
        {
            "name": "Bonao Cut & Style",
            "subdomain": "bonaocut",
            "admin_email": "manuel.vargas@auronsuite.com",
            "admin_name": "Manuel Vargas",
            "plan_name": "basic",
            "status": "cancelled",
            "phone": "8095554455",
            "address": "Av. Libertad, Bonao",
            "currency": "DOP",
            "poblar_detalles": False
        },
        {
            "name": "Peluquería Infantil Pequeños Estilos",
            "subdomain": "pequestilos",
            "admin_email": "diana.mercedes@auronsuite.com",
            "admin_name": "Diana Mercedes",
            "plan_name": "standard",
            "status": "active",
            "phone": "8095556677",
            "address": "Av. San Vicente de Paul, Santo Domingo Este",
            "currency": "DOP",
            "poblar_detalles": False
        },
        {
            "name": "Aura Centro Estético",
            "subdomain": "auraestetica",
            "admin_email": "sofia.castro@auronsuite.com",
            "admin_name": "Sofía Castro",
            "plan_name": "premium",
            "status": "suspended",
            "phone": "8095558899",
            "address": "Av. Luis Ginebra, Puerto Plata",
            "currency": "DOP",
            "poblar_detalles": False
        }
    ]

    for t_data in tenants_data:
        print(f"\n🏢 Creando Tenant: {t_data['name']} ({t_data['subdomain']})")

        # 1. Obtener plan
        plan = SubscriptionPlan.objects.filter(name=t_data["plan_name"]).first()
        if not plan:
            plan = SubscriptionPlan.objects.first()

        # 2. Crear administrador de negocio
        admin_user = User.objects.filter(email=t_data["admin_email"]).first()
        if not admin_user:
            admin_user = User(
                email=t_data["admin_email"],
                full_name=t_data["admin_name"],
                phone=t_data["phone"],
                is_active=True,
                is_email_verified=True,
                is_superuser=True,  # Temporal para evadir check de BD
                is_staff=True,
                tenant=None,
                role=None
            )
            admin_user.set_password("AuronPass2026*")
            admin_user.save(skip_validation=True)
            print(f"  ✓ Admin creado temporalmente: {t_data['admin_email']}")
        else:
            print(f"  ✓ Admin ya existe: {t_data['admin_email']}")

        # 3. Crear Tenant
        tenant = Tenant.objects.filter(subdomain=t_data["subdomain"]).first()
        if not tenant:
            tenant = Tenant.objects.create(
                name=t_data["name"],
                subdomain=t_data["subdomain"],
                owner=admin_user,
                contact_email=t_data["admin_email"],
                contact_phone=t_data["phone"],
                subscription_plan=plan,
                subscription_status=t_data["status"],
                is_active=(t_data["status"] not in ['suspended', 'expired']),
                trial_end_date=(timezone.now() + timedelta(days=14) if t_data["status"] == 'trial' else None)
            )
            print(f"  ✓ Tenant registrado en base de datos.")
        else:
            print(f"  ✓ Tenant ya existía.")

        # Asociar admin user al tenant y quitar privilegios globales
        admin_user.tenant = tenant
        admin_user.role = 'Client-Admin'
        admin_user.is_superuser = False
        admin_user.is_staff = False
        admin_user.save(skip_validation=True)

        # Asignar rol
        UserRole.objects.get_or_create(
            user=admin_user,
            role=client_admin_role,
            tenant=tenant
        )

        # Suscripción activa si aplica
        if t_data["status"] in ['active', 'trial']:
            UserSubscription.objects.get_or_create(
                user=admin_user,
                plan=plan,
                defaults={
                    'start_date': timezone.now() - timedelta(days=5),
                    'end_date': timezone.now() + timedelta(days=25),
                    'is_active': (t_data["status"] == 'active'),
                    'auto_renew': True
                }
            )

        # 4. Crear Sucursal
        branch = Branch.objects.filter(tenant=tenant).first()
        if not branch:
            branch = Branch.objects.create(
                tenant=tenant,
                name="Sucursal Principal",
                address=t_data["address"],
                is_main=True,
                is_active=True
            )
            print(f"  ✓ Sucursal Principal creada.")
        else:
            print(f"  ✓ Sucursal Principal ya existe (reutilizando {branch.name}).")

        # Configuración de sucursal
        Setting.objects.update_or_create(
            branch=branch,
            defaults={
                'business_name': tenant.name,
                'business_email': tenant.contact_email,
                'phone_number': t_data["phone"],
                'currency': t_data["currency"],
                'timezone': 'America/Santo_Domingo'
            }
        )

        # Configuración de POS
        PosConfiguration.objects.update_or_create(
            tenant=tenant,
            user=admin_user,
            defaults={
                'business_name': tenant.name,
                'address': branch.address,
                'phone': t_data["phone"],
                'email': tenant.contact_email,
                'currency': t_data["currency"],
                'currency_symbol': '$' if t_data["currency"] == 'USD' else 'RD$',
                'tax_rate': Decimal('0.1800') if t_data["currency"] == 'DOP' else Decimal('0.0700'),
                'tax_included': True
            }
        )

        # Población de detalles completos (servicios, empleados, ventas) si está habilitado
        if t_data["poblar_detalles"]:
            print(f"  🚀 Poblando datos transaccionales para {t_data['name']}...")
            
            # Categorías de Servicios
            cat_cortes, _ = ServiceCategory.objects.get_or_create(tenant=tenant, name="Cortes y Estilos", defaults={'description': 'Cortes clásicos y peinados'})
            cat_cuidado, _ = ServiceCategory.objects.get_or_create(tenant=tenant, name="Cuidado Personal", defaults={'description': 'Cuidado facial y corporal'})

            # Servicios
            corte_srv, _ = Service.objects.update_or_create(
                name="Corte de Pelo Estilo Moderno",
                tenant=tenant,
                branch=branch,
                defaults={
                    "price": Decimal("500.00") if t_data["currency"] == "DOP" else Decimal("25.00"),
                    "duration": 30,
                    "description": "Corte de pelo moderno con perfilado.",
                    "is_active": True
                }
            )
            corte_srv.categories.add(cat_cortes)

            facial_srv, _ = Service.objects.update_or_create(
                name="Tratamiento Facial Purificante",
                tenant=tenant,
                branch=branch,
                defaults={
                    "price": Decimal("800.00") if t_data["currency"] == "DOP" else Decimal("45.00"),
                    "duration": 40,
                    "description": "Limpieza facial completa.",
                    "is_active": True
                }
            )
            facial_srv.categories.add(cat_cuidado)

            # Categoría de Productos y Productos
            cat_prod, _ = ProductCategory.objects.get_or_create(tenant=tenant, name="Productos de Cuidado", defaults={"description": "Ceras y geles"})
            supplier, _ = Supplier.objects.get_or_create(name="Distribuidora Belleza Pro", tenant=tenant, defaults={"phone": "8095550000"})
            
            cera_prod, _ = Product.objects.update_or_create(
                sku="CER-001-" + t_data["subdomain"].upper(),
                tenant=tenant,
                branch=branch,
                defaults={
                    "name": "Cera Fijadora Efecto Mate",
                    "price": Decimal("750.00") if t_data["currency"] == "DOP" else Decimal("20.00"),
                    "stock": 20,
                    "min_stock": 3,
                    "supplier": supplier,
                    "category": cat_prod,
                    "is_active": True
                }
            )

            # Empleados
            emp_emails = [
                f"juan.{t_data['subdomain']}@auronsuite.com",
                f"maria.{t_data['subdomain']}@auronsuite.com"
            ]
            emp_names = ["Juan López", "María Rodríguez"]
            emp_profiles = []

            for idx, email in enumerate(emp_emails):
                emp_user = User.objects.filter(email=email).first()
                if not emp_user:
                    emp_user = User(
                        email=email,
                        full_name=emp_names[idx],
                        phone="809555" + str(random.randint(1000, 9999)),
                        is_active=True,
                        is_email_verified=True,
                        tenant=tenant,
                        role="Estilista"
                    )
                    emp_user.set_password("AuronEmpPass2026*")
                    emp_user.save(skip_validation=True)
                    
                    UserRole.objects.create(
                        user=emp_user,
                        role=estilista_role,
                        tenant=tenant
                    )

                emp_profile, _ = Employee.objects.update_or_create(
                    user=emp_user,
                    tenant=tenant,
                    defaults={
                        "branch": branch,
                        "profession": "barber" if idx == 0 else "stylist",
                        "phone": emp_user.phone,
                        "hire_date": timezone.now().date() - timedelta(days=30),
                        "payment_type": "commission",
                        "commission_rate": Decimal("40.00"),
                        "is_active": True
                    }
                )
                emp_profiles.append(emp_profile)

                # Horarios
                for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']:
                    WorkSchedule.objects.get_or_create(
                        employee=emp_profile,
                        day_of_week=day,
                        defaults={
                            'start_time': datetime.strptime("09:00:00", "%H:%M:%S").time(),
                            'end_time': datetime.strptime("18:00:00", "%H:%M:%S").time()
                        }
                    )

                # Asignar servicios
                ServiceEmployee.objects.get_or_create(service=corte_srv, employee=emp_profile, defaults={"commission_percentage": Decimal("40.00")})
                ServiceEmployee.objects.get_or_create(service=facial_srv, employee=emp_profile, defaults={"commission_percentage": Decimal("40.00")})

            # Clientes
            c_names = ["Carlos Durán", "Yinet Peralta"]
            c_emails = [f"carlos.duran@{t_data['subdomain']}.do", f"yinet.peralta@{t_data['subdomain']}.do"]
            clientes_tenant = []

            for idx, c_name in enumerate(c_names):
                client, _ = Client.objects.update_or_create(
                    full_name=c_name,
                    tenant=tenant,
                    defaults={
                        "email": c_emails[idx],
                        "phone": "809555" + str(random.randint(1000, 9999)),
                        "gender": "M" if idx == 0 else "F",
                        "branch": branch,
                        "is_active": True
                    }
                )
                clientes_tenant.append(client)

            # Caja registradora
            cash_register = CashRegister.objects.filter(tenant=tenant, is_open=True).first()
            if not cash_register:
                cash_register = CashRegister.objects.create(
                    tenant=tenant,
                    branch=branch,
                    user=admin_user,
                    initial_cash=Decimal("3000.00"),
                    is_open=True,
                    opened_at=timezone.now() - timedelta(hours=2)
                )

            # Citas y Ventas pasadas
            yesterday = timezone.now() - timedelta(days=1)
            date_cita = yesterday.replace(hour=11, minute=0, second=0, microsecond=0)
            
            c1, c1_created = Appointment.objects.get_or_create(
                tenant=tenant,
                branch=branch,
                client=clientes_tenant[0],
                stylist=emp_profiles[0].user,
                service=corte_srv,
                date_time=date_cita,
                defaults={'status': 'completed'}
            )

            if c1_created or not c1.sale:
                total_sale = corte_srv.price
                sale1 = Sale.objects.create(
                    tenant=tenant,
                    branch=branch,
                    user=admin_user,
                    employee=emp_profiles[0],
                    client=clientes_tenant[0],
                    cash_register=cash_register,
                    date_time=date_cita,
                    total=total_sale,
                    paid=total_sale,
                    payment_method='cash',
                    status='confirmed',
                    closed=True
                )

                ct_service = ContentType.objects.get_for_model(Service)
                SaleDetail.objects.create(
                    sale=sale1,
                    content_type=ct_service,
                    object_id=corte_srv.id,
                    name=corte_srv.name,
                    quantity=1,
                    price=corte_srv.price
                )

                Payment.objects.create(
                    sale=sale1,
                    method='cash',
                    amount=total_sale
                )

                c1.sale = sale1
                c1.save()

            # Citas programadas para hoy
            today = timezone.now()
            date_c2 = today.replace(hour=14, minute=30, second=0, microsecond=0)
            Appointment.objects.get_or_create(
                tenant=tenant,
                branch=branch,
                client=clientes_tenant[1],
                stylist=emp_profiles[1].user,
                service=facial_srv,
                date_time=date_c2,
                defaults={'status': 'scheduled'}
            )

    print("\n---------------------------------------------------------------------------------")
    print("🎉 ¡Se crearon con éxito 10 inquilinos realistas en la base de datos local!")
    print("📋 Puedes gestionar o inspeccionar todos estos negocios con el usuario Super-Admin:")
    print("👉 Email Super-Admin: alexanderadp@gmail.com")
    print("---------------------------------------------------------------------------------")

if __name__ == '__main__':
    seed_data()
