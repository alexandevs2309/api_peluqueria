"""
Pruebas end-to-end del endpoint de cobro del POS (asignación de barbero).

Verifica las reglas de negocio en el punto donde realmente occurre el problema:
la creación de la venta desde el cajero.

Reglas cubiertas:
  1. Cada línea de servicio recibe su propio barbero.
  2. Solo se aceptan empleados que briskten ese servicio.
  3. NUNCA se asigna un empleado automáticamente.
  4. Servicio sin barbero -> advertencia; requiere autorización + motivo.
  5. Se aceptan 'employee' y 'employee_id' (compatibilidad).
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.clients_api.models import Client
from apps.employees_api.models import Employee
from apps.inventory_api.models import Product
from apps.pos_api.models import CashRegister, Sale, SaleDetail
from apps.services_api.models import Service, ServiceEmployee
from apps.tenants_api.models import Tenant
from apps.audit_api.models import AuditLog

User = get_user_model()


def authenticate_client(client, user):
    client.force_authenticate(user=user)
    from rest_framework_simplejwt.tokens import AccessToken
    token = AccessToken.for_user(user)
    if getattr(user, 'tenant_id', None):
        token['tenant_id'] = user.tenant_id
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")
    client.cookies['access_token'] = str(token)


def _setup_plan(tenant):
    from apps.subscriptions_api.models import SubscriptionPlan
    plan, _ = SubscriptionPlan.objects.get_or_create(
        name='basic',
        defaults={
            'price': 0, 'max_users': 10, 'max_employees': 10,
            'features': {'cash_register': True, 'promotions': True},
        },
    )
    tenant.subscription_plan = plan
    tenant.save(update_fields=['subscription_plan'])


def _setup_rbac(user, tenant):
    from apps.roles_api.models import Role, UserRole
    role, _ = Role.objects.get_or_create(name='PosRole', defaults={'description': 'POS'})
    from django.contrib.auth.models import Permission
    perms = Permission.objects.filter(
        content_type__app_label__in=['pos_api', 'inventory_api', 'services_api']
    )
    role.permissions.add(*perms)
    UserRole.objects.get_or_create(user=user, role=role, tenant=tenant)


class TestPosEmployeeAssignmentAPI(APITestCase):
    def setUp(self):
        owner = User.objects.create_superuser(
            email='pos-owner@test.com', password='pass', full_name='Owner POS'
        )
        self.tenant = Tenant.objects.create(name='POS Test', subdomain='postest', owner=owner)
        _setup_plan(self.tenant)

        self.cashier = User.objects.create_user(
            email='pos-cashier@test.com', password='pass1234',
            tenant=self.tenant, full_name='Cajero POS',
        )
        _setup_rbac(self.cashier, self.tenant)
        self.cashier.is_staff = True
        self.cashier.save(update_fields=['is_staff'])

        self.register = CashRegister.objects.create(
            tenant=self.tenant, user=self.cashier,
            initial_cash=Decimal('0.00'), is_open=True,
        )

        # Servicios
        self.svc_corte = Service.objects.create(
            tenant=self.tenant, name='Corte', price=Decimal('1000.00'), duration=30
        )
        self.svc_color = Service.objects.create(
            tenant=self.tenant, name='Color', price=Decimal('2000.00'), duration=60
        )
        self.svc_orphan = Service.objects.create(
            tenant=self.tenant, name='Facial', price=Decimal('1500.00'), duration=45
        )
        self.product = Product.objects.create(
            tenant=self.tenant, name='Shampoo', price=Decimal('300.00'), stock=20
        )
        self.client_obj = Client.objects.create(
            tenant=self.tenant, full_name='Cliente POS', loyalty_points=0
        )

        # Empleados
        self.barber = Employee.objects.create(
            user=User.objects.create_user(
                email='pos-barber@test.com', password='x',
                tenant=self.tenant, full_name='Barbero Carlos',
            ),
            tenant=self.tenant, payment_type='commission',
            commission_rate=Decimal('40.00'), fixed_salary=Decimal('0.00'),
        )
        self.colorist = Employee.objects.create(
            user=User.objects.create_user(
                email='pos-colorist@test.com', password='x',
                tenant=self.tenant, full_name='Colorista Ana',
            ),
            tenant=self.tenant, payment_type='commission',
            commission_rate=Decimal('50.00'), fixed_salary=Decimal('0.00'),
        )

        # Solo el barbero presta cortes; solo la colorista presta color.
        ServiceEmployee.objects.create(employee=self.barber, service=self.svc_corte)
        ServiceEmployee.objects.create(employee=self.colorist, service=self.svc_color)

        authenticate_client(self.client, self.cashier)

    # ── helpers ───────────────────────────────────────────────────────────
    def _payload(self, details, **extra):
        total = sum(Decimal(str(d['price'])) * int(d.get('quantity', 1)) for d in details)
        payload = {
            'details': details,
            'payments': [{'method': 'cash', 'amount': total}],
            'total': str(total),
            'paid': str(total),
            'payment_method': 'cash',
        }
        payload.update(extra)
        return payload

    def _create_sale(self, details, **extra):
        return self.client.post(
            '/api/pos/sales/', self._payload(details, **extra), format='json'
        )

    # ── 1. Asignación por línea ────────────────────────────────────────────
    def test_two_services_two_barbers_in_one_sale(self):
        """Una venta con 2 servicios y 2 barberos: cada línea con el suyo."""
        r = self._create_sale([
            {'content_type': 'service', 'object_id': self.svc_corte.id,
             'name': 'Corte', 'quantity': 1, 'price': '1000.00',
             'employee': self.barber.id},
            {'content_type': 'service', 'object_id': self.svc_color.id,
             'name': 'Color', 'quantity': 1, 'price': '2000.00',
             'employee': self.colorist.id},
        ])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

        sale = Sale.objects.get(pk=r.data['id'])
        details = {d.name: d for d in sale.details.all()}

        self.assertEqual(details['Corte'].employee_id, self.barber.id)
        self.assertEqual(details['Color'].employee_id, self.colorist.id)

        # Snapshots por línea
        self.assertEqual(details['Corte'].commission_amount_snapshot, Decimal('400.00'))
        self.assertEqual(details['Color'].commission_amount_snapshot, Decimal('1000.00'))

        # Fuente única: snapshot de venta en NULL
        sale.refresh_from_db()
        self.assertIsNone(sale.commission_amount_snapshot)
        self.assertEqual(sale.commission_source, Sale.COMMISSION_SOURCE_LINE)

    def test_commission_reaches_payroll_for_each_barber(self):
        """Las comisiones por línea llegan a la nómina de cada barbero."""
        from apps.employees_api.earnings_models import PayrollPeriod

        r = self._create_sale([
            {'content_type': 'service', 'object_id': self.svc_corte.id,
             'name': 'Corte', 'quantity': 1, 'price': '1000.00',
             'employee': self.barber.id},
            {'content_type': 'service', 'object_id': self.svc_color.id,
             'name': 'Color', 'quantity': 1, 'price': '2000.00',
             'employee': self.colorist.id},
        ])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

        for employee, expected in ((self.barber, Decimal('400.00')),
                                   (self.colorist, Decimal('1000.00'))):
            period = PayrollPeriod.objects.filter(
                employee=employee, status__in=['open', 'pending_approval']
            ).first()
            self.assertIsNotNone(period, f'No hay período para {employee}')
            self.assertEqual(period.commission_earnings, expected)

    def test_product_does_not_generate_service_commission(self):
        """Los productos no generan comisión de servicios."""
        r = self._create_sale([
            {'content_type': 'service', 'object_id': self.svc_corte.id,
             'name': 'Corte', 'quantity': 1, 'price': '1000.00',
             'employee': self.barber.id},
            {'content_type': 'product', 'object_id': self.product.id,
             'name': 'Shampoo', 'quantity': 1, 'price': '300.00'},
        ])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

        sale = Sale.objects.get(pk=r.data['id'])
        product_line = sale.details.get(name='Shampoo')
        self.assertIsNone(product_line.employee_id)
        self.assertIsNone(product_line.commission_amount_snapshot)

    # ── 2. Validación de elegibilidad ──────────────────────────────────────
    def test_cannot_assign_employee_who_does_not_offer_service(self):
        """No se puede asignar al barbero a un servicio que no presta."""
        r = self._create_sale([
            {'content_type': 'service', 'object_id': self.svc_color.id,
             'name': 'Color', 'quantity': 1, 'price': '2000.00',
             'employee': self.barber.id},
        ])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('no presta', str(r.data).lower())

    def test_employee_from_another_tenant_is_rejected(self):
        """Un empleado de otro negocio no puede asignarse."""
        other_owner = User.objects.create_superuser(
            email='other-owner@test.com', password='pass', full_name='Other'
        )
        other_tenant = Tenant.objects.create(name='Other', subdomain='other', owner=other_owner)
        outsider = Employee.objects.create(
            user=User.objects.create_user(
                email='outsider@test.com', password='x',
                tenant=other_tenant, full_name='Outsider',
            ),
            tenant=other_tenant, payment_type='commission', commission_rate=Decimal('40.00'),
        )
        r = self._create_sale([
            {'content_type': 'service', 'object_id': self.svc_corte.id,
             'name': 'Corte', 'quantity': 1, 'price': '1000.00',
             'employee': outsider.id},
        ])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    # ── 3. Servicios sin barbero: nunca asignación automática ──────────────
    def test_service_without_barbers_is_rejected_without_authorization(self):
        """Un servicio sin empleados elegibles NO se puede vender sin más."""
        r = self._create_sale([
            {'content_type': 'service', 'object_id': self.svc_orphan.id,
             'name': 'Facial', 'quantity': 1, 'price': '1500.00'},
        ])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        msg = str(r.data).lower()
        self.assertIn('no tienen empleados elegibles', msg)
        self.assertIn('autoriza', msg)
        # Y lo más importante: no se creó la venta.
        self.assertFalse(Sale.objects.filter(status='confirmed').exists())

    def test_service_without_barbers_requires_reason_too(self):
        """Autorizar sin motivo no es suficiente."""
        r = self._create_sale(
            [{'content_type': 'service', 'object_id': self.svc_orphan.id,
              'name': 'Facial', 'quantity': 1, 'price': '1500.00'}],
            no_commission_authorization=True,
            no_commission_reason='corto',
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_authorized_without_commission_creates_no_commission(self):
        """Con autorización + motivo se vende, pero SIN comisión y con auditoría."""
        r = self._create_sale(
            [{'content_type': 'service', 'object_id': self.svc_orphan.id,
              'name': 'Facial', 'quantity': 1, 'price': '1500.00'}],
            no_commission_authorization=True,
            no_commission_reason='ClienteWalk-in sin barbero asignado en este momento',
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

        sale = Sale.objects.get(pk=r.data['id'])
        detail = sale.details.get(name='Facial')

        # No se inventó empleado ni comisión.
        self.assertIsNone(detail.employee_id)
        self.assertIsNone(detail.commission_amount_snapshot)
        self.assertEqual(sale.commission_source, Sale.COMMISSION_SOURCE_NONE)

        # Quedó registrado quién y por qué lo autorizó.
        log = AuditLog.objects.filter(
            description__icontains=f'Venta #{sale.id}'
        ).first()
        self.assertIsNotNone(log, 'Debe existir auditoría de la venta sin comisión')
        self.assertEqual(log.user_id, self.cashier.id)
        self.assertIn('Facial', log.extra_data['services_without_employee'])
        self.assertIn('Walk-in', log.extra_data['reason'])

    def test_no_employee_is_ever_auto_assigned(self):
        """Ninguna línea de servicio queda con barbero sin haberlo elegido."""
        self._create_sale([
            {'content_type': 'service', 'object_id': self.svc_corte.id,
             'name': 'Corte', 'quantity': 1, 'price': '1000.00',
             'employee': self.barber.id},
        ])
        # Solo la línea explícitamente asignada tiene empleado.
        assigned = SaleDetail.objects.exclude(employee__isnull=False).count()
        self.assertEqual(assigned, 0, 'No debe existir ninguna línea sin asignar que se haya auto-asignado')

    # ── 4. Compatibilidad del nombre del campo ────────────────────────────
    def test_accepts_employee_id_alias(self):
        """El payload con 'employee_id' también funciona."""
        r = self._create_sale([
            {'content_type': 'service', 'object_id': self.svc_corte.id,
             'name': 'Corte', 'quantity': 1, 'price': '1000.00',
             'employee_id': self.barber.id},
        ])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        sale = Sale.objects.get(pk=r.data['id'])
        self.assertEqual(sale.details.get(name='Corte').employee_id, self.barber.id)

    def test_sale_level_employee_field_is_accepted(self):
        """El frontend histórico envía 'employee' a nivel de venta.

        Este es el bug original: el backend leía 'employee_id' y nunca
        encontraba al empleado, por eso las ventas salían sin barbero y las
        comisiones quedaban en cero.

        El empleado a nivel de venta se aplica a las líneas de servicio que no
        declaren barbero, y la comisión se registra por línea (fuente única).
        """
        r = self._create_sale([
            {'content_type': 'service', 'object_id': self.svc_corte.id,
             'name': 'Corte', 'quantity': 1, 'price': '1000.00'},
        ], employee=self.barber.id)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

        sale = Sale.objects.get(pk=r.data['id'])
        sale.refresh_from_db()
        self.assertEqual(sale.employee_id, self.barber.id)

        detail = sale.details.get(name='Corte')
        self.assertEqual(detail.employee_id, self.barber.id)
        self.assertEqual(detail.commission_amount_snapshot, Decimal('400.00'))

        # Fuente única: con comisión por línea, la de venta queda en NULL.
        self.assertIsNone(sale.commission_amount_snapshot)
        self.assertEqual(sale.commission_source, Sale.COMMISSION_SOURCE_LINE)

    def test_repeated_service_commission_rate_uses_service_specific_config(self):
        """Si el servicio define un % propio, ese manda sobre el global."""
        ServiceEmployee.objects.filter(
            employee=self.barber, service=self.svc_corte
        ).update(commission_percentage=Decimal('60.00'))

        r = self._create_sale([
            {'content_type': 'service', 'object_id': self.svc_corte.id,
             'name': 'Corte', 'quantity': 1, 'price': '1000.00',
             'employee': self.barber.id},
        ])
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

        sale = Sale.objects.get(pk=r.data['id'])
        detail = sale.details.get(name='Corte')
        self.assertEqual(detail.commission_rate_snapshot, Decimal('60.00'))
        self.assertEqual(detail.commission_amount_snapshot, Decimal('600.00'))
        self.assertEqual(detail.commission_source, 'service')

    # ── 5. Venta que proviene de una cita ─────────────────────────────────
    def test_sale_from_appointment_inherits_the_stylist(self):
        """Si la venta viene de una cita, el barbero es el estilista de esa cita."""
        from apps.appointments_api.models import Appointment
        from apps.roles_api.models import Role

        role, _ = Role.objects.get_or_create(name='StylistRole', defaults={'description': 'x'})
        appointment = Appointment.objects.create(
            tenant=self.tenant,
            client=self.client_obj,
            stylist=self.barber.user,
            role=role,
            service=self.svc_corte,
            date_time=timezone.now() + timedelta(days=1),
            status='scheduled',
        )

        r = self._create_sale([
            {'content_type': 'service', 'object_id': self.svc_corte.id,
             'name': 'Corte', 'quantity': 1, 'price': '1000.00'},
        ], appointment=appointment.id)

        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        sale = Sale.objects.get(pk=r.data['id'])
        detail = sale.details.get(name='Corte')

        self.assertEqual(detail.employee_id, self.barber.id)
        self.assertEqual(detail.commission_amount_snapshot, Decimal('400.00'))
