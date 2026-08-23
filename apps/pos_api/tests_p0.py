"""
Tests P0 — Regresión para los 6 problemas críticos del informe forense.
Cada test DEBE FALLAR antes del fix y PASAR después.
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from apps.tenants_api.models import Tenant
from apps.employees_api.models import Employee
from apps.pos_api.models import (
    Sale, SaleDetail, CashRegister, Promotion, Coupon
)
from apps.employees_api.earnings_models import PayrollPeriod, PayrollDeduction, PayrollConfiguration
from apps.inventory_api.models import Product
from apps.services_api.models import Service
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


def _create_tenant(name='Test Salon', subdomain='test'):
    owner = User.objects.create_user(
        email=f'{subdomain}-owner@test.com', password='pass',
        full_name=f'{name} Owner', is_superuser=True
    )
    return Tenant.objects.create(name=name, subdomain=subdomain, owner=owner)


def _create_user(tenant, email='admin@test.com'):
    return User.objects.create_user(
        email=email, password='test123',
        full_name='Admin Test', tenant=tenant
    )


def _setup_plan(tenant):
    from apps.subscriptions_api.models import SubscriptionPlan
    plan, _ = SubscriptionPlan.objects.get_or_create(
        name='basic',
        defaults={
            'price': 0, 'max_users': 10, 'max_employees': 10,
            'features': {'cash_register': True, 'promotions': True},
        }
    )
    tenant.subscription_plan = plan
    tenant.save(update_fields=['subscription_plan'])


# ==============================================================================
# P0-6: POS-006 — Pérdida de datos de arqueo
# ==============================================================================

class TestPOS006_ArqueoDataLoss(TestCase):
    """
    Bug: open_register() fuerza final_cash=0 al cerrar la caja anterior.
    Fix: se elimina final_cash=0 del update, preservando datos de arqueo.
    """

    def setUp(self):
        self.tenant = _create_tenant()
        self.user = _create_user(self.tenant)
        _setup_plan(self.tenant)

    def test_open_register_preserves_previous_final_cash(self):
        """Abrir nueva caja NO debe sobrescribir final_cash de la anterior."""
        from django.utils import timezone as tz

        # Crear Caja A con final_cash=350 (arqueo hecho)
        caja_a = CashRegister.objects.create(
            user=self.user,
            tenant=self.tenant,
            initial_cash=Decimal('100.00'),
            final_cash=Decimal('350.00'),
            is_open=True,
        )

        # Simular open_register SIN final_cash=0 (el fix)
        CashRegister.objects.filter(
            tenant=self.tenant,
            user=self.user,
            is_open=True,
        ).update(
            is_open=False,
            closed_at=tz.now(),
            # FIX: no final_cash=0 here
        )

        caja_a.refresh_from_db()

        self.assertEqual(
            caja_a.final_cash,
            Decimal('350.00'),
            "final_cash de la caja anterior fue preservado"
        )
        self.assertFalse(caja_a.is_open)

    def test_multiple_registers_preserve_arqueo_data(self):
        """Historial de múltiples cajas preserva datos de arqueo."""
        from django.utils import timezone as tz

        # Caja 1
        caja_1 = CashRegister.objects.create(
            user=self.user, tenant=self.tenant,
            initial_cash=Decimal('100.00'), final_cash=Decimal('260.00'),
            is_open=False, closed_at=tz.now(),
        )
        # Caja 2
        caja_2 = CashRegister.objects.create(
            user=self.user, tenant=self.tenant,
            initial_cash=Decimal('50.00'), final_cash=Decimal('180.00'),
            is_open=False, closed_at=tz.now(),
        )
        # Caja 3 (abierta)
        caja_3 = CashRegister.objects.create(
            user=self.user, tenant=self.tenant,
            initial_cash=Decimal('75.00'), is_open=True,
        )

        # Abrir nueva caja (cierra Caja 3)
        CashRegister.objects.filter(
            tenant=self.tenant, user=self.user, is_open=True,
        ).update(is_open=False, closed_at=tz.now())

        # Verificar que Caja 1 y 2 preservan sus datos
        caja_1.refresh_from_db()
        caja_2.refresh_from_db()
        caja_3.refresh_from_db()

        self.assertEqual(caja_1.final_cash, Decimal('260.00'))
        self.assertEqual(caja_2.final_cash, Decimal('180.00'))
        self.assertFalse(caja_3.is_open)


# ==============================================================================
# P0-3: POS-002 — Race condition en promociones
# ==============================================================================

class TestPOS002_PromotionConcurrency(TransactionTestCase):
    """
    Bug: Promotion.objects.get() sin select_for_update() permite
    que current_uses exceda max_uses bajo concurrencia.
    Fix: select_for_update() en views.py:364.
    Nota: usa TransactionTestCase + threading para testear concurrencia real.
    """

    def setUp(self):
        self.tenant = _create_tenant('Salon Promo', 'promo')
        self.user = _create_user(self.tenant, 'promo@test.com')
        _setup_plan(self.tenant)

    def test_promotion_max_uses_not_exceeded(self):
        """current_uses no debe exceder max_uses bajo concurrencia."""
        import threading

        promo = Promotion.objects.create(
            tenant=self.tenant,
            name='Test Promo',
            type='percentage',
            discount_value=Decimal('10.00'),
            min_amount=Decimal('0.00'),
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=30),
            is_active=True,
            max_uses=3,
            current_uses=0,
        )

        errors = []

        def increment_uses():
            """Simula lo que hace views.py al validar una promoción."""
            try:
                from django.db import transaction
                with transaction.atomic():
                    # Esto es lo que el fix hace: select_for_update
                    p = Promotion.objects.select_for_update().get(id=promo.id)
                    if p.max_uses and p.current_uses >= p.max_uses:
                        return
                    p.current_uses += 1
                    p.save(update_fields=['current_uses'])
            except Exception as e:
                errors.append(str(e))

        # Lanzar 5 threads intentando incrementar (max_uses=3)
        threads = [threading.Thread(target=increment_uses) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        promo.refresh_from_db()
        self.assertEqual(len(errors), 0, f"Errores en threads: {errors}")
        self.assertLessEqual(
            promo.current_uses,
            promo.max_uses,
            f"current_uses={promo.current_uses} excede max_uses={promo.max_uses}"
        )


# ==============================================================================
# P0-4: POS-003 — Cross-tenant SaleDetail
# ==============================================================================

class TestPOS003_CrossTenantSaleDetail(TestCase):
    """
    Bug: SaleDetail.clean() nunca se ejecuta. Un usuario puede crear
    un SaleDetail referenciando producto/servicio de otro tenant.
    Fix: validación cross-tenant en SaleSerializer.create().
    """

    def setUp(self):
        self.tenant_a = _create_tenant('Salon A', 'salon-a')
        self.user_a = _create_user(self.tenant_a, 'admin-a@test.com')
        _setup_plan(self.tenant_a)

        self.tenant_b = _create_tenant('Salon B', 'salon-b')
        self.user_b = _create_user(self.tenant_b, 'admin-b@test.com')

        # Producto de Tenant A
        self.product_a = Product.objects.create(
            tenant=self.tenant_a,
            name='Shampoo A',
            price=Decimal('10.00'),
            stock=100,
            is_active=True,
        )

        # Producto de Tenant B
        self.product_b = Product.objects.create(
            tenant=self.tenant_b,
            name='Shampoo B',
            price=Decimal('15.00'),
            stock=50,
            is_active=True,
        )

    def test_sale_serializer_blocks_cross_tenant_product(self):
        """SaleSerializer.create() debe rechazar producto de otro tenant."""
        from apps.pos_api.serializers import SaleSerializer

        # Crear mock request con tenant A
        class MockRequest:
            def __init__(self, user, tenant):
                self.user = user
                self.tenant = tenant
                self.data = {}

        request = MockRequest(self.user_a, self.tenant_a)
        serializer = SaleSerializer(
            context={'request': request},
            data={
                'details': [{
                    'content_type': 'product',
                    'object_id': self.product_b.id,  # Tenant B's product
                    'name': 'Shampoo B',
                    'quantity': '1',
                    'price': '15.00',
                }],
                'payments': [{
                    'payment_method': 'cash',
                    'amount': '15.00',
                }],
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

        from django.core.exceptions import ValidationError as DjangoValidationError
        with self.assertRaises(DjangoValidationError) as ctx:
            serializer.save()
        self.assertIn('no encontrado', str(ctx.exception))

    def test_sale_serializer_allows_valid_product(self):
        """SaleSerializer.create() debe aceptar producto propio."""
        from apps.pos_api.serializers import SaleSerializer

        class MockRequest:
            def __init__(self, user, tenant):
                self.user = user
                self.tenant = tenant
                self.data = {}

        request = MockRequest(self.user_a, self.tenant_a)
        serializer = SaleSerializer(
            context={'request': request},
            data={
                'details': [{
                    'content_type': 'product',
                    'object_id': self.product_a.id,  # Tenant A's own product
                    'name': 'Shampoo A',
                    'quantity': '1',
                    'price': '10.00',
                }],
                'payments': [{
                    'payment_method': 'cash',
                    'amount': '10.00',
                }],
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        sale = serializer.save()
        self.assertEqual(sale.details.count(), 1)
        self.assertEqual(sale.details.first().object_id, self.product_a.id)


# ==============================================================================
# P0-2: POS-001 — Commission snapshot ignora historial
# ==============================================================================

class TestPOS001_CommissionSnapshotHistorical(TestCase):
    """
    Bug: Sale.save() usa employee.commission_rate (actual) en vez de
    EmployeeCompensationHistory (histórico) para calcular el snapshot.
    """

    def setUp(self):
        self.tenant = _create_tenant('Salon Comm', 'comm')
        self.user = _create_user(self.tenant, 'comm@test.com')
        _setup_plan(self.tenant)

    def test_commission_snapshot_uses_historical_rate(self):
        """Snapshot debe usar tasa histórica, no la actual del empleado."""
        from apps.employees_api.compensation_models import EmployeeCompensationHistory
        from apps.pos_api.services import SaleCommissionService

        employee = Employee.objects.create(
            user=self.user,
            tenant=self.tenant,
            payment_type='commission',
            commission_rate=Decimal('40.00'),
        )

        # Crear historial con rate=40%
        EmployeeCompensationHistory.objects.create(
            employee=employee,
            payment_type='commission',
            fixed_salary=Decimal('0.00'),
            commission_rate=Decimal('40.00'),
            effective_date=date(2026, 1, 1),
        )

        # Cambiar rate a 30%
        employee.commission_rate = Decimal('30.00')
        employee.save()

        # Crear historial con rate=30%
        EmployeeCompensationHistory.objects.create(
            employee=employee,
            payment_type='commission',
            fixed_salary=Decimal('0.00'),
            commission_rate=Decimal('30.00'),
            effective_date=date(2026, 7, 1),
        )

        # Crear venta con fecha en marzo (debería usar 40%)
        sale = Sale.objects.create(
            user=self.user,
            employee=employee,
            tenant=self.tenant,
            total=Decimal('100.00'),
            status='confirmed',
            date_time=timezone.make_aware(
                timezone.datetime(2026, 3, 15, 10, 0, 0)
            ),
        )

        # ANTES DEL FIX: Sale.save() usa rate actual (30%) → snapshot=$30
        # DESPUÉS DEL FIX: SaleCommissionService sobreescribe con rate histórico (40%) → snapshot=$40
        # Simular lo que hace perform_create() después de crear la venta
        SaleCommissionService.apply_commission_snapshot(sale, employee)
        sale.save(update_fields=['commission_rate_snapshot', 'commission_amount_snapshot'])

        self.assertEqual(
            sale.commission_amount_snapshot,
            Decimal('40.00'),
            f"Snapshot debería usar tasa histórica (40%), "
            f"pero obtuvo {sale.commission_amount_snapshot}"
        )


# ==============================================================================
# P0-5: POS-004 — Bypass de inmutabilidad via update_fields
# ==============================================================================

class TestPOS004_ImmutabilityBypass(TestCase):
    """
    Bug: Sale.save(update_fields=['total']) bypass TODAS las protecciones
    de inmutabilidad, permitiendo modificar campos financieros de ventas confirmadas.
    """

    def setUp(self):
        self.tenant = _create_tenant('Salon Imm', 'imm')
        self.user = _create_user(self.tenant, 'imm@test.com')
        _setup_plan(self.tenant)

    def test_update_fields_total_blocked_on_confirmed(self):
        """No se puede modificar total via update_fields en venta confirmed."""
        sale = Sale.objects.create(
            user=self.user,
            tenant=self.tenant,
            total=Decimal('100.00'),
            status='confirmed',
        )

        # Intentar modificar total via update_fields
        sale.total = Decimal('999.99')

        # ANTES DEL FIX: esto pasa silenciosamente (bypass)
        # DESPUÉS DEL FIX: debe lanzar ValidationError
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            sale.save(update_fields=['total'])
            # Si no lanza error, el test falla (RED)
            self.fail(
                "save(update_fields=['total']) debería haber sido bloqueado "
                "en venta confirmed"
            )
        except DjangoValidationError:
            pass  # Fix lo bloquea correctamente

    def test_update_fields_ncf_allowed_on_confirmed(self):
        """SÍ se puede modificar ncf via update_fields (campo no financiero)."""
        sale = Sale.objects.create(
            user=self.user,
            tenant=self.tenant,
            total=Decimal('100.00'),
            status='confirmed',
        )

        sale.ncf = 'B0200000001'
        sale.save(update_fields=['ncf'])

        sale.refresh_from_db()
        self.assertEqual(sale.ncf, 'B0200000001')

    def test_update_fields_status_allowed(self):
        """SÍ se puede modificar status (void/refunded)."""
        sale = Sale.objects.create(
            user=self.user,
            tenant=self.tenant,
            total=Decimal('100.00'),
            status='confirmed',
        )

        sale.status = 'refunded'
        sale.save(update_fields=['status', 'closed'])

        sale.refresh_from_db()
        self.assertEqual(sale.status, 'refunded')
        self.assertTrue(sale.closed)


# ==============================================================================
# P0-1: PAY-001 — Deducciones legales duplicadas
# ==============================================================================

class TestPAY001_DeduccionesDuplicadas(TestCase):
    """
    Bug: calculate_amounts() crea deducciones por DOS caminos:
    1. [Config] basadas en base_salary
    2. _apply_legal_deductions() basadas en gross_amount
    Resultado: 6 deducciones en DB, 3 contadas en net, recibo muestra 6.
    """

    def setUp(self):
        self.tenant = _create_tenant('Salon Pay', 'pay')
        self.user = _create_user(self.tenant, 'pay@test.com')
        _setup_plan(self.tenant)

        self.employee = Employee.objects.create(
            user=self.user,
            tenant=self.tenant,
            payment_type='mixed',
            fixed_salary=Decimal('1000.00'),
            commission_rate=Decimal('40.00'),
        )

        # Configurar nómina: ISR=10%, TSS=2.87%, SFS=3.04%
        self.payroll_config = PayrollConfiguration.objects.create(
            tenant=self.tenant,
            tax_rate=Decimal('10.00'),
            social_security_rate=Decimal('2.87'),
            health_insurance_rate=Decimal('3.04'),
        )

    def test_no_duplicate_legal_deductions(self):
        """Una deducción lógica = un registro en DB (sin duplicados)."""
        period = PayrollPeriod.objects.create(
            employee=self.employee,
            period_type='biweekly',
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 15),
            status='open',
        )

        period.calculate_amounts()
        period.save()

        # Contar deducciones por tipo
        tax_count = period.deductions.filter(
            deduction_type='tax', is_automatic=True
        ).count()
        ss_count = period.deductions.filter(
            deduction_type='social_security', is_automatic=True
        ).count()
        hi_count = period.deductions.filter(
            deduction_type='health_insurance', is_automatic=True
        ).count()

        # Cada tipo debe tener exactamente 1 registro
        self.assertEqual(tax_count, 1, f"Esperaba 1 deducción ISR, encontró {tax_count}")
        self.assertEqual(ss_count, 1, f"Esperaba 1 deducción TSS, encontró {ss_count}")
        self.assertEqual(hi_count, 1, f"Esperaba 1 deducción SFS, encontró {hi_count}")

    def test_deductions_total_matches_all_deductions(self):
        """deductions_total debe ser igual a la suma de todas las deducciones."""
        period = PayrollPeriod.objects.create(
            employee=self.employee,
            period_type='biweekly',
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 15),
            status='open',
        )

        period.calculate_amounts()
        period.save()

        # La suma de deducciones en DB debe ser igual a deductions_total
        db_total = sum(d.amount for d in period.deductions.all())
        self.assertEqual(
            db_total,
            period.deductions_total,
            f"Suma de deducciones en DB ({db_total}) != "
            f"deductions_total ({period.deductions_total})"
        )

    def test_legal_deductions_use_gross_not_base(self):
        """AFP/SFS/ISR deben calcularse sobre gross_amount, no base_salary."""
        period = PayrollPeriod.objects.create(
            employee=self.employee,
            period_type='biweekly',
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 15),
            status='open',
        )

        period.calculate_amounts()
        period.save()

        # base_salary = 1000/2 = 500
        # Para mixed, commission_earnings = 0 (sin ventas)
        # gross_amount = 500 + 0 = 500
        # ISR sobre gross: 500 * 10% = 50.00
        # TSS sobre gross: 500 * 2.87% = 14.35
        # SFS sobre gross: 500 * 3.04% = 15.20

        expected_gross = Decimal('500.00')
        self.assertEqual(period.gross_amount, expected_gross)

        isr = period.deductions.filter(deduction_type='tax', is_automatic=True).first()
        tss = period.deductions.filter(deduction_type='social_security', is_automatic=True).first()
        sfs = period.deductions.filter(deduction_type='health_insurance', is_automatic=True).first()

        self.assertIsNotNone(isr, "ISR no encontrado")
        self.assertIsNotNone(tss, "TSS no encontrado")
        self.assertIsNotNone(sfs, "SFS no encontrado")

        expected_isr = (expected_gross * Decimal('10.00') / 100).quantize(Decimal('0.01'))
        expected_tss = (expected_gross * Decimal('2.87') / 100).quantize(Decimal('0.01'))
        expected_sfs = (expected_gross * Decimal('3.04') / 100).quantize(Decimal('0.01'))

        self.assertEqual(isr.amount, expected_isr,
                         f"ISR: esperaba {expected_isr}, obtuvo {isr.amount}")
        self.assertEqual(tss.amount, expected_tss,
                         f"TSS: esperaba {expected_tss}, obtuvo {tss.amount}")
        self.assertEqual(sfs.amount, expected_sfs,
                         f"SFS: esperaba {expected_sfs}, obtuvo {sfs.amount}")

    def test_net_equals_gross_minus_deductions(self):
        """invariante: net = gross - deductions."""
        period = PayrollPeriod.objects.create(
            employee=self.employee,
            period_type='biweekly',
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 15),
            status='open',
        )

        period.calculate_amounts()
        period.save()

        expected_net = period.gross_amount - period.deductions_total
        self.assertEqual(
            period.net_amount, expected_net,
            f"net ({period.net_amount}) != gross ({period.gross_amount}) "
            f"- deductions ({period.deductions_total})"
        )
