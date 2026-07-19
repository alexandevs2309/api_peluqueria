"""
Management command: populate the tenant "Barberia Alexander" (id=4) with
realistic fake data covering every major module.

Usage (inside Docker):
    docker exec api_peluqueria-master-web-1 python manage.py seed_tenant_data
    docker exec api_peluqueria-master-web-1 python manage.py seed_tenant_data --clear
"""
import random
import decimal
from datetime import date, timedelta, datetime, time
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Populate Barberia Alexander (tenant=4) with realistic fake data"

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing data first')

    def handle(self, *args, **options):
        if options['clear']:
            self._clear_data()

        with transaction.atomic():
            self._run()

        self.stdout.write(self.style.SUCCESS('✅ Seed completed successfully'))

    # ─────────────────────────────────────────────
    # CLEAR
    # ─────────────────────────────────────────────
    def _clear_data(self):
        from apps.pos_api.models import Sale, SaleDetail, Payment as PosPayment, CashRegister, Receipt
        from apps.appointments_api.models import Appointment
        from apps.clients_api.models import Client, LoyaltyTransaction
        from apps.employees_api.models import (Employee, PayrollPeriod, PayrollDeduction,
                                                WorkSchedule, AttendanceRecord, Loan,
                                                CommissionAdjustment)
        from apps.services_api.models import Service, ServiceCategory, ServiceEmployee
        from apps.inventory_api.models import Product, ProductCategory, Supplier, StockMovement
        from apps.pos_api.models import Promotion, Coupon

        self.stdout.write('🗑️  Clearing existing data...')
        CommissionAdjustment.objects.all().delete()
        Receipt.objects.all().delete()
        PosPayment.objects.all().delete()
        SaleDetail.objects.all().delete()
        Sale.objects.all().delete()
        CashRegister.objects.all().delete()
        Appointment.objects.all().delete()
        LoyaltyTransaction.objects.all().delete()
        Client.objects.all().delete()
        PayrollDeduction.objects.all().delete()
        PayrollPeriod.objects.all().delete()
        WorkSchedule.objects.all().delete()
        AttendanceRecord.objects.all().delete()
        Loan.objects.all().delete()
        Employee.objects.all().delete()
        ServiceEmployee.objects.all().delete()
        Service.objects.all().delete()
        ServiceCategory.objects.all().delete()
        StockMovement.objects.all().delete()
        Product.objects.all().delete()
        ProductCategory.objects.all().delete()
        Supplier.objects.all().delete()
        Promotion.objects.all().delete()
        Coupon.objects.all().delete()

        # Delete staff users (keep owner + superadmin)
        User.objects.filter(
            tenant_id=4,
        ).exclude(
            email__in=['alexanderdelrosarioperez@gmail.com']
        ).delete()

        self.stdout.write('✅ Data cleared')

    # ─────────────────────────────────────────────
    # MAIN
    # ─────────────────────────────────────────────
    def _run(self):
        from apps.tenants_api.models import Tenant
        from apps.settings_api.models import Branch, Setting, BarbershopSettings
        from apps.subscriptions_api.models import SubscriptionPlan

        self.tenant = Tenant.objects.get(id=4)
        self.owner = User.objects.get(email='alexanderdelrosarioperez@gmail.com')

        # Ensure plan exists
        self.plan, _ = SubscriptionPlan.objects.get_or_create(
            name='standard',
            defaults={'price': 49.99, 'annual_price': 479.88, 'is_active': True, 'is_public': True,
                      'features': {'appointments': True, 'reports': True, 'multi_location': True,
                                   'custom_branding': True, 'priority_support': True}}
        )

        # Ensure branch
        self.branch, _ = Branch.objects.get_or_create(
            tenant=self.tenant, name='Principal',
            defaults={'is_main': True, 'is_active': True,
                      'address': 'Av. Winston Churchill #45, Santo Domingo'}
        )

        # Barbershop settings
        BarbershopSettings.objects.get_or_create(
            tenant=self.tenant,
            defaults={'name': 'Barberia Alexander', 'currency': 'DOP', 'currency_symbol': '$',
                      'primary_color': '#2563EB', 'secondary_color': '#4F46E5'}
        )

        now = timezone.now()
        today = now.date()

        # Create data
        employees = self._create_employees()
        service_cats, services = self._create_services(employees)
        prod_cats, suppliers, products = self._create_products()
        clients = self._create_clients()
        self._create_appointments(clients, employees, services)
        self._create_sales(clients, employees, services, products)
        self._create_payroll(employees)
        self._create_promotions()

        self.stdout.write(self.style.SUCCESS(
            f'\n📊 Seed Summary:\n'
            f'   Employees: {len(employees)}\n'
            f'   Services:  {len(services)}\n'
            f'   Products:  {len(products)}\n'
            f'   Clients:   {len(clients)}\n'
            f'   Branch:    {self.branch.name}\n'
        ))

    # ─────────────────────────────────────────────
    # EMPLOYEES
    # ─────────────────────────────────────────────
    def _create_employees(self):
        from apps.employees_api.models import Employee, WorkSchedule
        from faker import Faker
        fake = Faker('es_ES')

        professions = ['barber', 'stylist', 'barber_stylist', 'manicurist', 'receptionist']
        employees_data = [
            {'name': 'Carlos Martinez', 'profession': 'barber', 'rate': 40, 'payment': 'commission'},
            {'name': 'Maria Rodriguez', 'profession': 'stylist', 'rate': 35, 'payment': 'commission'},
            {'name': 'Juan Perez', 'profession': 'barber', 'rate': 50, 'payment': 'mixed',
             'salary': 15000},
            {'name': 'Ana Garcia', 'profession': 'manicurist', 'rate': 30, 'payment': 'commission'},
            {'name': 'Pedro Santos', 'profession': 'barber_stylist', 'rate': 45, 'payment': 'mixed',
             'salary': 12000},
            {'name': 'Laura Fernandez', 'profession': 'receptionist', 'rate': 0, 'payment': 'fixed',
             'salary': 18000},
        ]

        employees = []
        for data in employees_data:
            email = f"{data['name'].split()[0].lower()}@barberia.com"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'full_name': data['name'],
                    'phone': fake.phone_number()[:15],
                    'role': 'Estilista',
                    'business_role': 'professional',
                    'tenant': self.tenant,
                    'is_active': True,
                    'is_email_verified': True,
                }
            )
            if created:
                user.set_password('testpass123')
                user.save()

            # Crear UserRole para que el permisos por rol funcionen
            from apps.roles_api.models import UserRole, Role
            estilista_role, _ = Role.objects.get_or_create(name='Estilista')
            UserRole.objects.get_or_create(
                user=user,
                defaults={'role': estilista_role, 'tenant': self.tenant}
            )

            emp, _ = Employee.objects.get_or_create(
                user=user,
                defaults={
                    'tenant': self.tenant,
                    'branch': self.branch,
                    'profession': data['profession'],
                    'phone': user.phone or '',
                    'hire_date': fake.date_between(start_date='-6M', end_date='-1M'),
                    'is_active': True,
                    'payment_type': data['payment'],
                    'fixed_salary': data.get('salary', 0),
                    'commission_rate': data['rate'],
                }
            )
            employees.append(emp)

            # Work schedules (Mon-Sat 8am-6pm)
            for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']:
                WorkSchedule.objects.create(
                    employee=emp,
                    day_of_week=day,
                    start_time=time(8, 0),
                    end_time=time(18, 0),
                )

        self.stdout.write(f'  👤 Created {len(employees)} employees')
        return employees

    # ─────────────────────────────────────────────
    # SERVICES
    # ─────────────────────────────────────────────
    def _create_services(self, employees):
        from apps.services_api.models import Service, ServiceCategory, ServiceEmployee

        categories_data = [
            ('Cortes', ['Corte de cabello', 'Corte degradado', 'Corte con tijera', 'Corte infantil',
                        'Corte + Barba', 'Afeitado']),
            ('Barba', ['Arreglo de barba', 'Barba completa', 'Diseño de barba']),
            ('Tratamientos', ['Tratamiento capilar', 'Keratina', 'Tinte de cabello', 'Mechas']),
            ('Manicure y Pedicure', ['Manicure', 'Pedicure', 'Manicure + Pedicure', 'Uñas acrílicas']),
            ('Otros', ['Lavado y secado', 'Alisado', 'Cejas']),
        ]

        prices = {
            'Cortes': (200, 800),
            'Barba': (150, 500),
            'Tratamientos': (500, 2500),
            'Manicure y Pedicure': (300, 1200),
            'Otros': (100, 600),
        }

        durations = {
            'Cortes': (20, 45),
            'Barba': (15, 30),
            'Tratamientos': (45, 120),
            'Manicure y Pedicure': (30, 60),
            'Otros': (15, 60),
        }

        service_cats = []
        all_services = []

        for cat_name, service_names in categories_data:
            cat, _ = ServiceCategory.objects.get_or_create(
                name=cat_name, tenant=self.tenant,
                defaults={'is_active': True}
            )
            service_cats.append(cat)

            for svc_name in service_names:
                price_range = prices[cat_name]
                dur_range = durations[cat_name]

                svc, _ = Service.objects.get_or_create(
                    name=svc_name, tenant=self.tenant,
                    defaults={
                        'price': decimal.Decimal(random.randint(*price_range)),
                        'duration': random.randint(*dur_range),
                        'is_active': True,
                        'branch': self.branch,
                    }
                )
                svc.categories.add(cat)
                all_services.append(svc)

                # Assign 2-4 random employees
                assigned = random.sample(employees, k=min(random.randint(2, 4), len(employees)))
                for emp in assigned:
                    ServiceEmployee.objects.get_or_create(
                        service=svc, employee=emp,
                        defaults={'commission_percentage': emp.commission_rate}
                    )

        self.stdout.write(f'  💇 Created {len(all_services)} services in {len(service_cats)} categories')
        return service_cats, all_services

    # ─────────────────────────────────────────────
    # PRODUCTS
    # ─────────────────────────────────────────────
    def _create_products(self):
        from apps.inventory_api.models import Product, ProductCategory, Supplier, StockMovement

        suppliers_data = [
            ('Distribuidora BarberPro', '809-555-0101', 'ventas@barberpro.com'),
            ('Mayorista Belleza RD', '809-555-0202', 'pedidos@bellezard.com'),
            ('Importaciones Groom', '809-555-0303', 'info@groom.do'),
        ]
        suppliers = []
        for name, phone, email in suppliers_data:
            sup, _ = Supplier.objects.get_or_create(
                name=name, tenant=self.tenant,
                defaults={'phone': phone, 'email': email}
            )
            suppliers.append(sup)

        categories_data = [
            ('Cuidado Capilar', ['Shampoo Profesional', 'Acondicionador Reparador',
                                  'Mascarilla Hidratante', 'Aceite Capilar']),
            ('Estilizado', ['Pomada Matte', 'Gel Fijador Fuerte', 'Cera Texturizante',
                             'Spray Fijador']),
            ('Barberia', ['Crema de Afeitar', 'After Shave Balm', 'Espuma de Afeitar',
                           'Aceite para Barba']),
            ('Accesorios', ['Peine Profesional', 'Tijeras Barbear', 'Mantilla para Tinte',
                             'Brocha Barba']),
        ]

        prod_cats = []
        all_products = []

        for cat_name, prod_names in categories_data:
            cat, _ = ProductCategory.objects.get_or_create(
                name=cat_name, tenant=self.tenant,
                defaults={'is_active': True}
            )
            prod_cats.append(cat)

            for prod_name in prod_names:
                sku = f"SKU-{random.randint(1000, 9999)}"
                product, _ = Product.objects.get_or_create(
                    sku=sku, tenant=self.tenant,
                    defaults={
                        'name': prod_name,
                        'price': decimal.Decimal(random.randint(150, 2500)),
                        'stock': random.randint(5, 50),
                        'min_stock': random.randint(1, 5),
                        'is_active': True,
                        'category': cat,
                        'supplier': random.choice(suppliers),
                        'branch': self.branch,
                        'barcode': str(random.randint(100000000, 999999999)),
                    }
                )
                all_products.append(product)

                # Stock movements
                if product.stock > 0:
                    StockMovement.objects.create(
                        product=product,
                        quantity=product.stock,
                        reason='Inventario inicial'
                    )

        self.stdout.write(f'  📦 Created {len(all_products)} products in {len(prod_cats)} categories')
        return prod_cats, suppliers, all_products

    # ─────────────────────────────────────────────
    # CLIENTS
    # ─────────────────────────────────────────────
    def _create_clients(self):
        from apps.clients_api.models import Client
        from faker import Faker
        fake = Faker('es_ES')

        clients = []
        for i in range(30):
            gender = random.choice(['M', 'F', 'O'])
            first = fake.first_name_male() if gender == 'M' else fake.first_name_female()
            last = fake.last_name()
            full_name = f"{first} {last}"

            client, _ = Client.objects.get_or_create(
                full_name=full_name, tenant=self.tenant,
                defaults={
                    'email': fake.email(),
                    'phone': fake.phone_number()[:15],
                    'birthday': fake.date_of_birth(minimum_age=18, maximum_age=70),
                    'gender': gender,
                    'loyalty_points': random.randint(0, 500),
                    'source': random.choice(['walk_in', 'referral', 'social_media', 'google', '']),
                    'is_active': True,
                    'branch': self.branch,
                    'created_by': self.owner,
                }
            )
            clients.append(client)

        self.stdout.write(f'  👥 Created {len(clients)} clients')
        return clients

    # ─────────────────────────────────────────────
    # APPOINTMENTS
    # ─────────────────────────────────────────────
    def _create_appointments(self, clients, employees, services):
        from apps.appointments_api.models import Appointment

        now = timezone.now()
        appointments = []

        # Past appointments (last 30 days)
        for _ in range(40):
            days_ago = random.randint(1, 30)
            hour = random.randint(8, 17)
            dt = (now - timedelta(days=days_ago)).replace(hour=hour, minute=random.choice([0, 15, 30, 45]))

            stylists = [e.user for e in employees if e.profession in ('barber', 'stylist', 'barber_stylist')]
            if not stylists:
                stylists = [e.user for e in employees]

            appt = Appointment.objects.create(
                tenant=self.tenant,
                branch=self.branch,
                client=random.choice(clients),
                stylist=random.choice(stylists),
                service=random.choice(services),
                date_time=dt,
                status=random.choice(['completed', 'completed', 'completed', 'cancelled', 'no_show']),
            )
            appointments.append(appt)

        # Today's appointments
        today_base = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_hours = [9, 10, 11, 13, 14, 15, 16]
        stylists = [e.user for e in employees if e.profession in ('barber', 'stylist', 'barber_stylist')]
        if not stylists:
            stylists = [e.user for e in employees]

        for hour in today_hours[:random.randint(3, 6)]:
            dt = today_base.replace(hour=hour, minute=random.choice([0, 30]))
            appt = Appointment.objects.create(
                tenant=self.tenant,
                branch=self.branch,
                client=random.choice(clients),
                stylist=random.choice(stylists),
                service=random.choice(services),
                date_time=dt,
                status=random.choice(['scheduled', 'scheduled', 'completed']),
            )
            appointments.append(appt)

        # Future appointments (next 14 days)
        for _ in range(20):
            days_ahead = random.randint(1, 14)
            hour = random.randint(8, 17)
            dt = (now + timedelta(days=days_ahead)).replace(hour=hour, minute=random.choice([0, 30]))

            appt = Appointment.objects.create(
                tenant=self.tenant,
                branch=self.branch,
                client=random.choice(clients),
                stylist=random.choice(stylists),
                service=random.choice(services),
                date_time=dt,
                status='scheduled',
            )
            appointments.append(appt)

        self.stdout.write(f'  📅 Created {len(appointments)} appointments')
        return appointments

    # ─────────────────────────────────────────────
    # SALES (POS)
    # ─────────────────────────────────────────────
    def _create_sales(self, clients, employees, services, products):
        from apps.pos_api.models import Sale, SaleDetail, Payment as PosPayment, CashRegister, Receipt
        from apps.inventory_api.models import StockMovement
        from django.contrib.contenttypes.models import ContentType

        now = timezone.now()
        today = now.date()

        # Cash register
        cash_register, _ = CashRegister.objects.get_or_create(
            tenant=self.tenant,
            is_open=True,
            defaults={
                'branch': self.branch,
                'user': self.owner,
                'initial_cash': decimal.Decimal('2000.00'),
            }
        )

        # Get content types
        from apps.services_api.models import Service as SvcModel
        from apps.inventory_api.models import Product as ProdModel
        service_ct = ContentType.objects.get_for_model(SvcModel)
        product_ct = ContentType.objects.get_for_model(ProdModel)

        payment_methods = ['cash', 'card', 'transfer']
        sales = []

        # Sales from last 30 days
        for day_offset in range(30):
            sale_date = today - timedelta(days=day_offset)
            num_sales = random.randint(2, 8)

            for _ in range(num_sales):
                hour = random.randint(8, 17)
                dt = timezone.make_aware(datetime.combine(sale_date, time(hour, random.choice([0, 15, 30, 45]))))

                # 1-3 items per sale
                num_items = random.randint(1, 3)
                sale_total = decimal.Decimal('0')

                sale = Sale.objects.create(
                    tenant=self.tenant,
                    branch=self.branch,
                    user=self.owner,
                    employee=random.choice(employees) if random.random() > 0.3 else None,
                    client=random.choice(clients) if random.random() > 0.4 else None,
                    cash_register=cash_register,
                    date_time=dt,
                    total=0,
                    paid=0,
                    payment_method=random.choice(payment_methods),
                    status='draft',
                    closed=True,
                )

                for _ in range(num_items):
                    if random.random() > 0.4 and services:
                        svc = random.choice(services)
                        price = svc.price
                        SaleDetail.objects.create(
                            sale=sale,
                            content_type=service_ct,
                            object_id=svc.pk,
                            name=svc.name,
                            quantity=1,
                            price=price,
                        )
                        sale_total += price
                    elif products:
                        prod = random.choice(products)
                        qty = random.randint(1, 3)
                        price = prod.price
                        SaleDetail.objects.create(
                            sale=sale,
                            content_type=product_ct,
                            object_id=prod.pk,
                            name=prod.name,
                            quantity=qty,
                            price=price,
                        )
                        sale_total += price * qty

                # Apply random discount sometimes
                discount = decimal.Decimal('0')
                if random.random() > 0.8:
                    discount = (sale_total * decimal.Decimal(str(random.uniform(0.05, 0.15)))).quantize(decimal.Decimal('0.01'))

                final_total = sale_total - discount
                sale.total = final_total
                sale.discount = discount
                sale.paid = final_total
                sale.save()

                # Payment record
                PosPayment.objects.create(
                    sale=sale,
                    method=sale.payment_method,
                    amount=final_total,
                )

                # Receipt
                Receipt.objects.create(
                    sale=sale,
                    receipt_number=f"REC-{sale.id:06d}",
                )

                sales.append(sale)

        self.stdout.write(f'  💰 Created {len(sales)} sales')
        return sales

    # ─────────────────────────────────────────────
    # PAYROLL
    # ─────────────────────────────────────────────
    def _create_payroll(self, employees):
        from apps.employees_api.models import PayrollPeriod, PayrollDeduction

        today = timezone.now().date()
        periods = []

        for emp in employees:
            # Create 3 biweekly periods
            for i in range(3):
                start = today - timedelta(days=(i * 15) + 15)
                end = start + timedelta(days=14)

                base = emp.fixed_salary or decimal.Decimal('0')
                # Commission based on random sales volume
                sales_volume = decimal.Decimal(str(random.randint(8000, 25000)))
                commission = (sales_volume * decimal.Decimal(str(emp.commission_rate)) / 100).quantize(decimal.Decimal('0.01'))

                gross = base + commission
                deductions = (gross * decimal.Decimal('0.10')).quantize(decimal.Decimal('0.01'))
                net = gross - deductions

                statuses = ['paid', 'paid', 'open']
                status = statuses[i] if i < len(statuses) else 'open'

                pp = PayrollPeriod.objects.create(
                    employee=emp,
                    period_type='biweekly',
                    period_start=start,
                    period_end=end,
                    status=status,
                    payment_type_snapshot=emp.payment_type,
                    fixed_salary_snapshot=emp.fixed_salary,
                    commission_rate_snapshot=emp.commission_rate,
                    base_salary=base,
                    commission_earnings=commission,
                    gross_amount=gross,
                    deductions_total=deductions,
                    net_amount=net,
                    payment_method='transfer' if status == 'paid' else None,
                    paid_at=timezone.now() if status == 'paid' else None,
                    paid_by=self.owner if status == 'paid' else None,
                )

                # Add deductions
                if deductions > 0:
                    PayrollDeduction.objects.create(
                        period=pp,
                        deduction_type='tax',
                        amount=(gross * decimal.Decimal('0.10')).quantize(decimal.Decimal('0.01')),
                        description='ISR - Impuesto sobre la renta',
                        is_automatic=True,
                    )

                periods.append(pp)

        self.stdout.write(f'  💼 Created {len(periods)} payroll periods')
        return periods

    # ─────────────────────────────────────────────
    # PROMOTIONS & COUPONS
    # ─────────────────────────────────────────────
    def _create_promotions(self):
        from apps.pos_api.models import Promotion, Coupon
        from faker import Faker
        fake = Faker('es_ES')

        now = timezone.now()

        promos_data = [
            ('2x1 en Cortes', 'percentage', 50, 'Martes y jueves 2x1 en cortes de caballero'),
            ('Descuento Navidad', 'fixed', 100, 'Descuento especial de fin de ano'),
            ('Combo Barba + Corte', 'percentage', 15, '15% de descuento al hacer combo barba + corte'),
        ]

        for name, ptype, value, desc in promos_data:
            Promotion.objects.get_or_create(
                name=name, tenant=self.tenant,
                defaults={
                    'description': desc,
                    'type': ptype,
                    'discount_value': decimal.Decimal(value),
                    'start_date': now - timedelta(days=30),
                    'end_date': now + timedelta(days=60),
                    'is_active': True,
                    'max_uses': random.randint(50, 200),
                    'current_uses': random.randint(5, 30),
                }
            )

        coupons_data = [
            ('BIENVENIDO10', 'percentage', 10, 'Cupon de bienvenida'),
            ('BARBERIA20', 'fixed', 200, 'Descuento especial para nuevos clientes'),
            ('FIEL15', 'percentage', 15, 'Descuento para clientes frecuentes'),
        ]

        for code, ctype, value, desc in coupons_data:
            Coupon.objects.get_or_create(
                code=code, tenant=self.tenant,
                defaults={
                    'description': desc,
                    'type': ctype,
                    'value': decimal.Decimal(value),
                    'min_purchase_amount': decimal.Decimal(500),
                    'start_date': now - timedelta(days=30),
                    'end_date': now + timedelta(days=90),
                    'is_active': True,
                    'max_uses': 100,
                    'current_uses': random.randint(0, 20),
                }
            )

        self.stdout.write(f'  🏷️  Created {len(promos_data)} promotions, {len(coupons_data)} coupons')
