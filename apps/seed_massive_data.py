"""
Seed masivo de datos de prueba para AURON Suite.
Crea 10 tenants con datos completos: servicios, empleados, clientes, citas, ventas, etc.

Uso:
    python manage.py shell < apps/seed_massive_data.py
"""
import os
import sys
import random
import unicodedata
from decimal import Decimal
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
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
from apps.pos_api.models import Sale, SaleDetail, Payment, CashRegister, PosConfiguration, NCFSequence, Promotion, Coupon

User = get_user_model()

# ============================================================
# DATOS BASE
# ============================================================

TENANTS_DATA = [
    {
        "name": "Barberia y Spa El Elegante",
        "subdomain": "elegante",
        "admin_email": "alexander.delrosario@auronsuite.com",
        "admin_name": "Alexander Del Rosario",
        "plan_name": "standard",
        "status": "active",
        "phone": "8095551234",
        "address": "Av. Gustavo Mejia Ricart 45, Ensanche Naco, Santo Domingo",
        "currency": "USD",
        "country": "DO",
        "poblar": True,
        "num_branches": 3,
        "num_employees": 6,
        "num_clients": 15,
        "num_sales": 50,
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
        "currency": "USD",
        "country": "DO",
        "poblar": True,
        "num_branches": 2,
        "num_employees": 5,
        "num_clients": 12,
        "num_sales": 40,
    },
    {
        "name": "D'Carlos Barber Shop",
        "subdomain": "dcarlos",
        "admin_email": "carlos.mendez@auronsuite.com",
        "admin_name": "Carlos Mendez",
        "plan_name": "basic",
        "status": "active",
        "phone": "8095551122",
        "address": "Calle Del Sol 12, Santiago de los Caballeros",
        "currency": "USD",
        "country": "DO",
        "poblar": True,
        "num_branches": 1,
        "num_employees": 3,
        "num_clients": 10,
        "num_sales": 30,
    },
    {
        "name": "Senses Spa & Wellness",
        "subdomain": "senses",
        "admin_email": "laura.santos@auronsuite.com",
        "admin_name": "Laura Santos",
        "plan_name": "premium",
        "status": "active",
        "phone": "8295553344",
        "address": "Boulevard Turistico del Este, Punta Cana",
        "currency": "USD",
        "country": "DO",
        "poblar": True,
        "num_branches": 2,
        "num_employees": 5,
        "num_clients": 12,
        "num_sales": 35,
    },
    {
        "name": "Salon Miradas Express",
        "subdomain": "miradas",
        "admin_email": "clara.guzman@auronsuite.com",
        "admin_name": "Clara Guzman",
        "plan_name": "standard",
        "status": "trial",
        "phone": "8095555566",
        "address": "Av. Libertad 88, San Francisco de Macoris",
        "currency": "USD",
        "country": "DO",
        "poblar": True,
        "num_branches": 1,
        "num_employees": 3,
        "num_clients": 8,
        "num_sales": 20,
    },
    {
        "name": "The Gentleman's Club",
        "subdomain": "gentleman",
        "admin_email": "roberto.alvarez@auronsuite.com",
        "admin_name": "Roberto Alvarez",
        "plan_name": "enterprise",
        "status": "active",
        "phone": "8095559900",
        "address": "Av. Santa Rosa, La Romana",
        "currency": "USD",
        "country": "DO",
        "poblar": True,
        "num_branches": 3,
        "num_employees": 6,
        "num_clients": 15,
        "num_sales": 50,
    },
    {
        "name": "Glow Hair & Nails",
        "subdomain": "glow",
        "admin_email": "patricia.reyes@auronsuite.com",
        "admin_name": "Patricia Reyes",
        "plan_name": "standard",
        "status": "active",
        "phone": "8295552233",
        "address": "Calle Principal, Las Terrenas, Samana",
        "currency": "USD",
        "country": "DO",
        "poblar": True,
        "num_branches": 1,
        "num_employees": 3,
        "num_clients": 8,
        "num_sales": 20,
    },
    {
        "name": "Bonao Cut & Style",
        "subdomain": "bonaocut",
        "admin_email": "manuel.vargas@auronsuite.com",
        "admin_name": "Manuel Vargas",
        "plan_name": "basic",
        "status": "expired",
        "phone": "8095554455",
        "address": "Av. Libertad, Bonao",
        "currency": "USD",
        "country": "DO",
        "poblar": False,
        "num_branches": 1,
        "num_employees": 0,
        "num_clients": 0,
        "num_sales": 0,
    },
    {
        "name": "Peluqueria Infantil Pequenos Estilos",
        "subdomain": "pequestilos",
        "admin_email": "diana.mercedes@auronsuite.com",
        "admin_name": "Diana Mercedes",
        "plan_name": "standard",
        "status": "suspended",
        "phone": "8095556677",
        "address": "Av. San Vicente de Paul, Santo Domingo Este",
        "currency": "USD",
        "country": "DO",
        "poblar": False,
        "num_branches": 1,
        "num_employees": 0,
        "num_clients": 0,
        "num_sales": 0,
    },
    {
        "name": "Aura Centro Estetico",
        "subdomain": "auraestetica",
        "admin_email": "sofia.castro@auronsuite.com",
        "admin_name": "Sofia Castro",
        "plan_name": "premium",
        "status": "cancelled",
        "phone": "8095558899",
        "address": "Av. Luis Ginebra, Puerto Plata",
        "currency": "USD",
        "country": "DO",
        "poblar": False,
        "num_branches": 1,
        "num_employees": 0,
        "num_clients": 0,
        "num_sales": 0,
    },
]

SERVICE_CATALOG = {
    "DOP": [
        ("Cortes y Estilos", [
            ("Corte de Pelo Masculino", 400, 30),
            ("Corte de Pelo Femenino", 600, 45),
            ("Corte de Nino", 300, 20),
            ("Degradado / Fade", 500, 35),
            ("Corte con Barba", 600, 40),
            ("Alisado Capilar", 1500, 90),
        ]),
        ("Cuidado Personal", [
            ("Tratamiento Facial Purificante", 800, 40),
            ("Mascara Facial Hidratante", 700, 35),
            ("Limpieza Facial Profunda", 1200, 60),
            ("Cejas y Pestañas", 400, 20),
        ]),
        ("Manicure y Pedicure", [
            ("Manicure Basico", 500, 30),
            ("Pedicure Completo", 700, 45),
            ("Manicure con Gel", 900, 50),
            ("Spa de Manos", 600, 35),
        ]),
        ("Masajes y Relajacion", [
            ("Masaje Descontracturante", 1200, 60),
            ("Masaje Relajante", 1000, 50),
            ("Masaje con Aceites Esenciales", 1500, 75),
        ]),
        ("Color y Tratamiento", [
            ("Tinte de Cabello", 2000, 90),
            ("Mechones / Highlighting", 2500, 120),
            ("Tratamiento Capilar Keratina", 3000, 120),
            ("Corte y Tinte", 2200, 120),
        ]),
    ],
    "USD": [
        ("Hair Services", [
            ("Men's Haircut", 20, 30),
            ("Women's Haircut", 35, 45),
            ("Kids' Haircut", 15, 20),
            ("Fade / Undercut", 25, 35),
            ("Haircut + Beard", 30, 40),
            ("Hair Straightening", 75, 90),
        ]),
        ("Facial & Skin", [
            ("Purifying Facial Treatment", 45, 40),
            ("Hydrating Face Mask", 40, 35),
            ("Deep Cleansing Facial", 65, 60),
            ("Eyebrow Shaping", 20, 20),
        ]),
        ("Nail Services", [
            ("Basic Manicure", 25, 30),
            ("Full Pedicure", 35, 45),
            ("Gel Manicure", 45, 50),
            ("Hand Spa Treatment", 30, 35),
        ]),
        ("Massage & Relaxation", [
            ("Deep Tissue Massage", 60, 60),
            ("Relaxation Massage", 50, 50),
            ("Aromatherapy Massage", 75, 75),
        ]),
        ("Color & Treatment", [
            ("Hair Coloring", 100, 90),
            ("Highlights", 120, 120),
            ("Keratin Treatment", 150, 120),
            ("Cut & Color Combo", 110, 120),
        ]),
    ],
}

PRODUCT_CATALOG = {
    "DOP": [
        ("Productos de Cuidado", "Belleza Pro RD", [
            ("Cera Fijadora Efecto Mate", "CER-001", 750, 25),
            ("Gel de Fijacion Fuerte", "GEL-001", 500, 30),
            ("Shampoo Anticaspa", "SHP-001", 450, 20),
            ("Acondicionador Hidratante", "ACD-001", 480, 20),
            ("Aceite para Barba", "ACE-001", 600, 15),
        ]),
        ("Herramientas", "Distribuidora Bella RD", [
            ("Peine de Bolsillo", "PEI-001", 150, 40),
            ("Tijera Profesional", "TIJ-001", 2500, 5),
            ("Kit de Corte Basico", "KIT-001", 3500, 3),
        ]),
        ("Accesorios", "Accesorios Total RD", [
            ("Toalla de Salon (unidad)", "TOW-001", 250, 30),
            ("Mantilla para Cliente", "MAN-001", 350, 15),
            ("Bata de Barbero", "BAT-001", 800, 10),
        ]),
    ],
    "USD": [
        ("Hair Care Products", "Beauty Pro Supply", [
            ("Matte Finish Pomade", "POM-001", 20, 25),
            ("Strong Hold Gel", "GEL-002", 15, 30),
            ("Anti-Dandruff Shampoo", "SHP-002", 12, 20),
            ("Moisturizing Conditioner", "ACD-002", 14, 20),
            ("Beard Oil", "ACE-002", 18, 15),
        ]),
        ("Tools", "Salon Supply USA", [
            ("Pocket Comb", "PEI-002", 5, 40),
            ("Professional Scissors", "TIJ-002", 80, 5),
            ("Basic Clipper Kit", "KIT-002", 120, 3),
        ]),
        ("Accessories", "Salon Accessories Co", [
            ("Salon Towel (unit)", "TOW-002", 8, 30),
            ("Client Cape", "MAN-002", 12, 15),
            ("Barber Apron", "BAT-002", 25, 10),
        ]),
    ],
}

NAMES_M = [
    "Carlos Duran", "Miguel Rodriguez", "Juan Peralta", "Roberto Diaz",
    "Pedro Martinez", "Luis Fernandez", "Diego Garcia", "Manuel Lopez",
    "Jose Ramirez", "Antonio Torres", "Francisco Castillo", "Ricardo Sanchez",
    "Fernando Perez", "Santiago Morales", "Gabriel Herrera", "Andres Cruz",
    "Rafael Vargas", "Tomas Ramirez", "Oscar Mejia", "Sergio Aquino",
]
NAMES_F = [
    "Yinet Peralta", "Maria Rodriguez", "Ana Martinez", "Carmen Diaz",
    "Rosa Garcia", "Laura Lopez", "Patricia Ramirez", "Sofia Torres",
    "Isabel Castillo", "Elena Sanchez", "Valentina Perez", "Camila Morales",
    "Daniela Herrera", "Lucia Cruz", "Adriana Vargas", "Monica Ramirez",
    "Claudia Mejia", "Teresa Aquino", "Natalia Fernandez", "Gabriela Santos",
]

ADDRESSES_RD = [
    "Av. Winston Churchill, Santo Domingo",
    "Calle El Conde, Zona Colonial",
    "Av. 27 de Febrero, Santo Domingo",
    "Av. John F. Kennedy, Santo Domingo",
    "Calle Las Damas, Zona Colonial",
    "Av. Independencia, Santo Domingo",
    "Av. George Washington, Malecon",
    "Calle Padres Castellanos, Santo Domingo",
    "Av. Roberto Pastoriza, Santo Domingo",
    "Av. Sarasota, Santo Domingo",
]

SOURCES = ["Instagram", "Referido", "Trafico local", "Google Maps", "Facebook", "Walk-in", "TikTok"]


# ============================================================
# HELPERS
# ============================================================

def _is_dop(currency):
    return currency == "DOP"

def _get_price(base, currency, variance=0.2):
    if currency == "USD":
        return Decimal(str(round(base * (1 + random.uniform(-variance, variance)), 2)))
    return Decimal(str(round(base * (1 + random.uniform(-variance, variance)), 2)))

def _random_phone():
    return f"809{random.randint(5550000, 5559999)}"

def _random_email(name, subdomain):
    parts = name.split()
    first = unicodedata.normalize('NFKD', parts[0].lower()).encode('ascii', 'ignore').decode()
    last = unicodedata.normalize('NFKD', parts[-1].lower()).encode('ascii', 'ignore').decode()
    return f"{first}.{last}@{subdomain}.test"

def _random_date(days_back=30):
    now = timezone.now()
    delta = timedelta(days=random.randint(0, days_back))
    hour = random.choice([9,10,10,11,11,11,12,14,14,15,15,16,16,17])
    minute = random.choice([0,15,30,45])
    return (now - delta).replace(hour=hour, minute=minute, second=0, microsecond=0)

def _random_future_date(days_ahead=14):
    now = timezone.now()
    delta = timedelta(days=random.randint(1, days_ahead))
    hour = random.choice([9,10,11,14,15,16,17])
    minute = random.choice([0,15,30,45])
    return (now + delta).replace(hour=hour, minute=minute, second=0, microsecond=0)


# ============================================================
# FUNCIONES DE CREACION
# ============================================================

def create_admin(t_data):
    admin = User.objects.filter(email=t_data["admin_email"]).first()
    if admin:
        return admin
    admin = User(
        email=t_data["admin_email"],
        full_name=t_data["admin_name"],
        phone=t_data["phone"],
        is_active=True,
        is_email_verified=True,
        is_superuser=True,
        is_staff=True,
        tenant=None,
        role=None,
    )
    admin.set_password("AuronPass2026*")
    admin.save(skip_validation=True)
    return admin


def create_tenant(t_data, plan, admin, client_admin_role):
    tenant = Tenant.objects.filter(subdomain=t_data["subdomain"]).first()
    if tenant:
        return tenant
    tenant = Tenant.objects.create(
        name=t_data["name"],
        subdomain=t_data["subdomain"],
        owner=admin,
        contact_email=t_data["admin_email"],
        contact_phone=t_data["phone"],
        address=t_data["address"],
        country=t_data.get("country", "DO"),
        currency=t_data["currency"],
        subscription_plan=plan,
        subscription_status=t_data["status"],
        is_active=(t_data["status"] not in ["suspended", "expired", "cancelled"]),
        trial_end_date=(timezone.now() + timedelta(days=14) if t_data["status"] == "trial" else None),
    )
    admin.tenant = tenant
    admin.role = "Client-Admin"
    admin.is_superuser = False
    admin.is_staff = False
    admin.save(skip_validation=True)
    UserRole.objects.get_or_create(user=admin, role=client_admin_role, tenant=tenant)
    if t_data["status"] in ["active", "trial"]:
        UserSubscription.objects.get_or_create(
            user=admin, plan=plan,
            defaults={
                "start_date": timezone.now() - timedelta(days=5),
                "end_date": timezone.now() + timedelta(days=25),
                "is_active": (t_data["status"] == "active"),
                "auto_renew": True,
            },
        )
    return tenant


def create_branches(tenant, t_data, count):
    branches = []
    branch_names = ["Sucursal Principal", "Sucursal Norte", "Sucursal Este", "Sucursal VIP"]
    for i in range(count):
        branch, _ = Branch.objects.get_or_create(
            tenant=tenant, name=branch_names[i],
            defaults={
                "address": t_data["address"] if i == 0 else f"{t_data['address']} - Sucursal {i+1}",
                "is_main": (i == 0),
                "is_active": True,
            },
        )
        Setting.objects.update_or_create(
            branch=branch,
            defaults={
                "business_name": tenant.name,
                "business_email": tenant.contact_email,
                "phone_number": t_data["phone"],
                "currency": t_data["currency"],
                "timezone": "America/Santo_Domingo",
            },
        )
        branches.append(branch)
    return branches


def create_pos_config(tenant, admin, t_data, branch):
    PosConfiguration.objects.update_or_create(
        tenant=tenant, user=admin,
        defaults={
            "business_name": tenant.name,
            "address": branch.address,
            "phone": t_data["phone"],
            "email": tenant.contact_email,
            "rnc": f"{random.randint(100000000, 199999999)}",
            "currency": t_data["currency"],
            "currency_symbol": "$" if not _is_dop(t_data["currency"]) else "RD$",
            "tax_rate": Decimal("0.1800") if _is_dop(t_data["currency"]) else Decimal("0.0700"),
            "tax_included": True,
        },
    )
    NCFSequence.objects.get_or_create(
        tenant=tenant, type="02", prefix="B",
        start_sequence=1,
        defaults={
            "end_sequence": 99999999,
            "current_sequence": 1,
            "expiration_date": date.today() + timedelta(days=365),
            "is_active": True,
        },
    )


def create_services(tenant, branch, currency):
    catalog = SERVICE_CATALOG.get(currency, SERVICE_CATALOG["DOP"])
    all_services = []
    for cat_name, services in catalog:
        cat, _ = ServiceCategory.objects.get_or_create(
            tenant=tenant, name=cat_name,
            defaults={"description": f"Categoria de {cat_name}"},
        )
        for srv_name, base_price, duration in services:
            price = _get_price(base_price, currency)
            srv, _ = Service.objects.update_or_create(
                name=srv_name, tenant=tenant, branch=branch,
                defaults={
                    "price": price,
                    "duration": duration,
                    "description": f"Servicio profesional: {srv_name}",
                    "is_active": True,
                },
            )
            srv.categories.add(cat)
            all_services.append(srv)
    return all_services


def create_products(tenant, branch, currency):
    catalog = PRODUCT_CATALOG.get(currency, PRODUCT_CATALOG["DOP"])
    all_products = []
    for cat_name, supplier_name, products in catalog:
        cat, _ = ProductCategory.objects.get_or_create(
            tenant=tenant, name=cat_name,
            defaults={"description": f"Categoria de {cat_name}"},
        )
        supplier, _ = Supplier.objects.get_or_create(
            name=supplier_name, tenant=tenant,
            defaults={"phone": _random_phone(), "email": f"ventas@{supplier_name.lower().replace(' ','')}.do"},
        )
        for prod_name, sku_base, base_price, stock in products:
            price = _get_price(base_price, currency)
            p, _ = Product.objects.update_or_create(
                sku=f"{sku_base}-{tenant.subdomain.upper()}",
                tenant=tenant,
                branch=branch,
                defaults={
                    "name": prod_name,
                    "price": price,
                    "stock": stock,
                    "min_stock": max(3, stock // 5),
                    "supplier": supplier,
                    "category": cat,
                    "is_active": True,
                },
            )
            all_products.append(p)
    return all_products


def create_employees(tenant, branch, roles, count, currency):
    professions = ["barber", "stylist", "manicurist", "colorist", "massage", "barber_stylist"]
    employees = []
    used_names = set()
    for i in range(count):
        pool = NAMES_M if i % 2 == 0 else NAMES_F
        available = [n for n in pool if n not in used_names]
        if not available:
            available = pool
        name = random.choice(available)
        used_names.add(name)
        email = _random_email(name, tenant.subdomain)
        user = User.objects.filter(email=email).first()
        if not user:
            user = User(
                email=email, full_name=name,
                phone=_random_phone(),
                is_active=True, is_email_verified=True,
                tenant=tenant, role="Estilista",
            )
            user.set_password("AuronEmpPass2026*")
            user.save(skip_validation=True)
            UserRole.objects.get_or_create(user=user, role=roles["estilista"], tenant=tenant)
        prof = professions[i % len(professions)]
        emp, _ = Employee.objects.update_or_create(
            user=user, tenant=tenant,
            defaults={
                "branch": branch,
                "profession": prof,
                "phone": user.phone,
                "hire_date": (timezone.now() - timedelta(days=random.randint(30, 365))).date(),
                "payment_type": random.choice(["commission", "commission", "fixed", "mixed"]),
                "fixed_salary": Decimal(str(random.choice([15000, 18000, 20000, 25000]) if _is_dop(currency) else random.choice([400, 500, 600]))),
                "commission_rate": Decimal(str(random.choice([30, 35, 40, 45, 50]))),
                "is_active": True,
            },
        )
        for day in ["monday","tuesday","wednesday","thursday","friday","saturday"]:
            WorkSchedule.objects.get_or_create(
                employee=emp, day_of_week=day,
                defaults={
                    "start_time": datetime.strptime(random.choice(["08:00","09:00"]), "%H:%M").time(),
                    "end_time": datetime.strptime(random.choice(["17:00","18:00","19:00"]), "%H:%M").time(),
                },
            )
        employees.append(emp)
    return employees


def create_clients(tenant, branch, count):
    clients = []
    used_names = set()
    for i in range(count):
        pool = NAMES_M + NAMES_F
        available = [n for n in pool if n not in used_names]
        if not available:
            available = pool
        name = random.choice(available)
        used_names.add(name)
        gender = "M" if name in NAMES_M else "F"
        client, _ = Client.objects.update_or_create(
            full_name=name, tenant=tenant,
            defaults={
                "email": _random_email(name, tenant.subdomain),
                "phone": _random_phone(),
                "gender": gender,
                "branch": branch,
                "birthday": date.today() - timedelta(days=random.randint(7000, 18000)),
                "source": random.choice(SOURCES),
                "loyalty_points": random.randint(0, 500),
                "is_active": True,
            },
        )
        clients.append(client)
    return clients


def create_transactions(tenant, branch, admin, services, products, employees, clients, num_sales, currency):
    if not services or not employees or not clients:
        return
    ct_service = ContentType.objects.get(app_label="services_api", model="service")
    ct_product = ContentType.objects.get(app_label="inventory_api", model="product")

    cash_register = CashRegister.objects.create(
        tenant=tenant, branch=branch, user=admin,
        initial_cash=Decimal(str(random.choice([2000, 3000, 5000]) if _is_dop(currency) else random.choice([50, 100, 200]))),
        is_open=True,
        opened_at=timezone.now() - timedelta(hours=random.randint(1, 4)),
    )

    for i in range(num_sales):
        sale_date = _random_date(30)
        client = random.choice(clients)
        emp = random.choice(employees)
        service = random.choice(services)
        qty_services = random.randint(1, 2)
        total = service.price * qty_services
        product = None
        if random.random() < 0.4 and products:
            product = random.choice(products)
            total += product.price

        sale = Sale.objects.create(
            tenant=tenant, branch=branch, user=admin, employee=emp,
            client=client, cash_register=cash_register,
            date_time=sale_date, total=total, paid=total,
            payment_method=random.choice(["cash","cash","card","card","transfer"]),
            status="confirmed", closed=True,
        )
        SaleDetail.objects.create(
            sale=sale, content_type=ct_service, object_id=service.id,
            name=service.name, quantity=qty_services, price=service.price,
        )
        if product:
            SaleDetail.objects.create(
                sale=sale, content_type=ct_product, object_id=product.id,
                name=product.name, quantity=1, price=product.price,
            )
        Payment.objects.create(sale=sale, method=sale.payment_method, amount=total)

        Appointment.objects.create(
            tenant=tenant, branch=branch, client=client,
            stylist=emp.user, service=service,
            date_time=sale_date, status="completed", sale=sale,
        )

        if product and product.stock > 0:
            StockMovement.objects.create(
                product=product, quantity=-random.randint(1, min(3, product.stock)),
                reason=f"Venta #{sale.id}",
            )

    for _ in range(num_sales // 4):
        client = random.choice(clients)
        emp = random.choice(employees)
        service = random.choice(services)
        Appointment.objects.create(
            tenant=tenant, branch=branch, client=client,
            stylist=emp.user, service=service,
            date_time=_random_future_date(14), status="scheduled",
        )

    for _ in range(num_sales // 8):
        client = random.choice(clients)
        emp = random.choice(employees)
        service = random.choice(services)
        Appointment.objects.create(
            tenant=tenant, branch=branch, client=client,
            stylist=emp.user, service=service,
            date_time=_random_date(15), status=random.choice(["cancelled", "no_show"]),
        )


# ============================================================
# MAIN
# ============================================================

DEFAULT_PLANS = [
    {
        "name": "basic",
        "description": "Plan básico para barberías individuales",
        "price": Decimal("29.99"),
        "annual_price": Decimal("299.99"),
        "max_employees": 3,
        "max_users": 5,
        "allows_multiple_branches": False,
        "features": {
            "cash_register": True, "appointments": True, "inventory": True,
            "reports": True, "basic_reports": True, "client_history": True,
            "promotions": False, "multi_location": False, "advanced_reports": False,
            "payroll": False, "custom_branding": False, "whatsapp_notifications": False,
            "export_reports": False, "priority_support": False,
        },
    },
    {
        "name": "standard",
        "description": "Plan Pro para negocios en crecimiento",
        "price": Decimal("59.99"),
        "annual_price": Decimal("599.99"),
        "max_employees": 10,
        "max_users": 15,
        "allows_multiple_branches": True,
        "features": {
            "cash_register": True, "appointments": True, "inventory": True,
            "reports": True, "basic_reports": True, "client_history": True,
            "promotions": True, "multi_location": True, "advanced_reports": True,
            "payroll": True, "custom_branding": False, "whatsapp_notifications": False,
            "export_reports": False, "priority_support": False,
        },
    },
    {
        "name": "premium",
        "description": "Plan Business para spas y salones consolidados",
        "price": Decimal("99.99"),
        "annual_price": Decimal("999.99"),
        "max_employees": 25,
        "max_users": 30,
        "allows_multiple_branches": True,
        "features": {
            "cash_register": True, "appointments": True, "inventory": True,
            "reports": True, "basic_reports": True, "client_history": True,
            "promotions": True, "multi_location": True, "advanced_reports": True,
            "payroll": True, "custom_branding": True, "whatsapp_notifications": True,
            "export_reports": False, "priority_support": False,
        },
    },
    {
        "name": "enterprise",
        "description": "Plan Enterprise ilimitado para cadenas y franquicias",
        "price": Decimal("199.99"),
        "annual_price": Decimal("1999.99"),
        "max_employees": 0,
        "max_users": 0,
        "allows_multiple_branches": True,
        "features": {
            "cash_register": True, "appointments": True, "inventory": True,
            "reports": True, "basic_reports": True, "client_history": True,
            "promotions": True, "multi_location": True, "advanced_reports": True,
            "payroll": True, "custom_branding": True, "whatsapp_notifications": True,
            "export_reports": True, "priority_support": True,
        },
    },
]


def ensure_subscription_plans():
    for p_data in DEFAULT_PLANS:
        plan, created = SubscriptionPlan.objects.update_or_create(
            name=p_data["name"],
            defaults=p_data,
        )
        if not created:
            print(f"  [PLAN] Actualizado: {plan.get_name_display()} - features: {plan.features}")


def ensure_superuser():
    super_admin_role = Role.objects.filter(name="SuperAdmin").first() or Role.objects.filter(name="Super-Admin").first()
    su = User.objects.filter(email="alexanderadp@gmail.com").first()
    if not su:
        su = User(
            email="alexanderadp@gmail.com",
            full_name="Alexander Perez",
            is_active=True,
            is_email_verified=True,
            is_superuser=True,
            is_staff=True,
            tenant=None,
            role="SuperAdmin",
        )
        su.set_password("AdminSuperPass2026*")
        su.save(skip_validation=True)
    if super_admin_role:
        UserRole.objects.get_or_create(user=su, role=super_admin_role, tenant=None)
    return su


def seed_all():
    print("=" * 70)
    print("  AURON SUITE — SEED MASIVO DE DATOS DE PRUEBA")
    print("=" * 70)

    ensure_subscription_plans()
    ensure_superuser()

    roles = {
        "admin": Role.objects.get(name="Client-Admin"),
        "estilista": Role.objects.get(name="Estilista"),
        "cajera": Role.objects.get(name="Cajera"),
    }
    for r in roles.values():
        ensure_role_default_permissions(r)

    plan_cache = {}
    total_stats = {"tenants": 0, "branches": 0, "employees": 0, "clients": 0, "sales": 0, "appointments": 0, "products": 0, "services": 0}

    for t_data in TENANTS_DATA:
        sub = t_data["subdomain"]
        print(f"\n{'─' * 60}")
        print(f"  Tenant: {t_data['name']} ({sub}) — Status: {t_data['status']}")
        print(f"{'─' * 60}")

        plan_name = t_data["plan_name"]
        if plan_name not in plan_cache:
            plan_cache[plan_name] = SubscriptionPlan.objects.filter(name=plan_name).first() or SubscriptionPlan.objects.first()
        plan = plan_cache[plan_name]

        admin = create_admin(t_data)
        tenant = create_tenant(t_data, plan, admin, roles["admin"])
        branches = create_branches(tenant, t_data, t_data["num_branches"])
        main_branch = branches[0]

        create_pos_config(tenant, admin, t_data, main_branch)

        if not t_data["poblar"]:
            print(f"  [SKIP] Tenant sin detalles (status={t_data['status']})")
            total_stats["tenants"] += 1
            total_stats["branches"] += len(branches)
            continue

        services = create_services(tenant, main_branch, t_data["currency"])
        products = create_products(tenant, main_branch, t_data["currency"])
        employees = create_employees(tenant, main_branch, roles, t_data["num_employees"], t_data["currency"])
        clients = create_clients(tenant, main_branch, t_data["num_clients"])

        create_transactions(
            tenant, main_branch, admin, services, products,
            employees, clients, t_data["num_sales"], t_data["currency"],
        )

        for branch in branches[1:]:
            create_services(tenant, branch, t_data["currency"])
            create_products(tenant, branch, t_data["currency"])

        total_stats["tenants"] += 1
        total_stats["branches"] += len(branches)
        total_stats["employees"] += len(employees)
        total_stats["clients"] += len(clients)
        total_stats["sales"] += t_data["num_sales"]
        total_stats["appointments"] += t_data["num_sales"] + t_data["num_sales"] // 4 + t_data["num_sales"] // 8
        total_stats["services"] += len(services)
        total_stats["products"] += len(products)

        print(f"  OK: {len(branches)} branches, {len(employees)} employees, {len(clients)} clients")
        print(f"      {len(services)} services, {len(products)} products, {t_data['num_sales']} sales")

    print("\n" + "=" * 70)
    print("  RESUMEN FINAL")
    print("=" * 70)
    for k, v in total_stats.items():
        print(f"  {k:>15}: {v}")
    print("=" * 70)
    print("\n  Credenciales Super-Admin: alexanderadp@gmail.com")
    print("  Credenciales Admin Tenant: AuronPass2026*")
    print("  Credenciales Empleados:    AuronEmpPass2026*")
    print("=" * 70)


if __name__ == "__main__" or True:
    seed_all()
