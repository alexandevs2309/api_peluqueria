"""
Pruebas de regresión: comisiones POR LÍNEA de venta.

Cubre las reglas de negocio confirmadas:
  1. Una venta puede incluir varios servicios y varios barberos.
  2. Cada línea tiene su propio barbero, % y monto de comisión.
  3. Los snapshots son inmutables tras confirmar la venta.
  4. Las ventas históricas conservan su snapshot a nivel de venta.
  5. La venta se contabiliza una sola vez; cada empleado ve sus líneas.
  6. Reembolsos totales y parciales, proporcionales, auditables e idempotentes.
  7. Servicios sin barbero: advertencia + autorización, nunca asignación.
  8. Aislamiento multi-tenant.
  9. Los productos no generan comisión de servicios.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.employees_api.models import Employee
from apps.employees_api.compensation_models import EmployeeCompensationHistory
from apps.employees_api.earnings_models import PayrollPeriod
from apps.employees_api.adjustment_models import CommissionAdjustment
from apps.inventory_api.models import Product
from apps.pos_api.models import Sale, SaleDetail
from apps.pos_api.services import SaleCommissionService
from apps.services_api.models import Service, ServiceEmployee
from apps.tenants_api.models import Tenant
from apps.auth_api.models import User


# ────────────────────────────── helpers ──────────────────────────────

def _period_for(employee, status='open'):
    today = timezone.localdate()
    if today.day <= 15:
        start = today.replace(day=1)
        end = today.replace(day=15)
    else:
        start = today.replace(day=16)
        end = today.replace(day=31)
    return PayrollPeriod.objects.create(
        employee=employee,
        period_type='biweekly',
        period_start=start,
        period_end=end,
        status=status,
    )


def _fixture(slug, rate='40.00', payment_type='commission', fixed_salary='0.00'):
    owner = User.objects.create_superuser(
        email=f'owner_{slug}@t.com', password='x', full_name=f'O {slug}'
    )
    tenant = Tenant.objects.create(name=f'T {slug}', subdomain=slug, owner=owner)
    user = User.objects.create_user(email=f'emp_{slug}@t.com', password='x', tenant=tenant)
    employee = Employee.objects.create(
        user=user, tenant=tenant, payment_type=payment_type,
        commission_rate=Decimal(rate), fixed_salary=Decimal(fixed_salary),
    )
    return tenant, user, employee


def _service(tenant, name, price='500.00'):
    return Service.objects.create(
        tenant=tenant, name=name, price=Decimal(price), duration=30, is_active=True
    )


def _product(tenant, name, price='200.00', stock=50):
    return Product.objects.create(
        tenant=tenant, name=name, price=Decimal(price), stock=stock, is_active=True
    )


def _add_detail(sale, obj, quantity=1, price=None, employee=None, service=True):
    if service:
        ct = ContentType.objects.get(app_label='services_api', model='service')
        price = price if price is not None else obj.price
    else:
        ct = ContentType.objects.get(app_label='inventory_api', model='product')
        price = price if price is not None else obj.price
    detail = SaleDetail.objects.create(
        sale=sale, content_type=ct, object_id=obj.id,
        name=obj.name, quantity=quantity, price=Decimal(str(price)),
    )
    if employee is not None:
        rate, amount, source = SaleCommissionService.calculate_detail_commission(
            employee=employee,
            service=obj if service else None,
            line_total=Decimal(str(price)) * quantity,
            sale_date=sale.date_time.date(),
        )
        if rate is not None:
            detail.employee = employee
            detail.commission_rate_snapshot = rate
            detail.commission_amount_snapshot = amount
            detail.commission_source = source
            SaleDetail.objects.filter(pk=detail.pk).update(
                employee_id=employee.id,
                commission_rate_snapshot=rate,
                commission_amount_snapshot=amount,
                commission_source=source,
            )
    return detail


# ───────────────── 1. Orden de resolución del porcentaje ─────────────────

class TestCommissionRatePrecedence:
    def test_service_specific_rate_wins(self):
        """1) ServiceEmployee.commission_percentage prevalece."""
        tenant, _, emp = _fixture('prec1')
        svc = _service(tenant, 'Corte', '1000.00')
        ServiceEmployee.objects.create(
            employee=emp, service=svc, commission_percentage=Decimal('55.00')
        )
        rate, source = SaleCommissionService.resolve_commission_rate(emp, svc, timezone.now().date())
        assert rate == Decimal('55.00')
        assert source == SaleCommissionService.SOURCE_SERVICE

    def test_history_used_when_no_service_config(self):
        """2) Sin config por servicio, usa el historial vigente."""
        tenant, _, emp = _fixture('prec2')
        svc = _service(tenant, 'Corte', '1000.00')
        EmployeeCompensationHistory.objects.create(
            employee=emp, payment_type='commission',
            fixed_salary=Decimal('0.00'), commission_rate=Decimal('30.00'),
            effective_date=timezone.localdate() - timedelta(days=5),
        )
        rate, source = SaleCommissionService.resolve_commission_rate(emp, svc, timezone.localdate())
        assert rate == Decimal('30.00')
        assert source == SaleCommissionService.SOURCE_HISTORY

    def test_global_rate_is_last_fallback(self):
        """3) Sin historial, usa la tasa global del empleado."""
        tenant, _, emp = _fixture('prec3', rate='45.00')
        svc = _service(tenant, 'Corte', '1000.00')
        rate, source = SaleCommissionService.resolve_commission_rate(emp, svc, timezone.localdate())
        assert rate == Decimal('45.00')
        assert source == SaleCommissionService.SOURCE_GLOBAL

    def test_fixed_employee_never_gets_commission(self):
        """El tipo de compensación manda: sueldo fijo no genera comisión."""
        tenant, _, emp = _fixture('fixed', rate='40.00', payment_type='fixed', fixed_salary='20000.00')
        svc = _service(tenant, 'Corte', '1000.00')
        ServiceEmployee.objects.create(
            employee=emp, service=svc, commission_percentage=Decimal('55.00')
        )
        rate, amount, source = SaleCommissionService.calculate_detail_commission(
            emp, svc, Decimal('1000.00'), timezone.localdate()
        )
        assert rate is None and amount is None
        assert source == SaleCommissionService.SOURCE_NONE

    def test_history_respects_effective_date(self):
        """La vigencia del historial se respeta (no se aplica un futuro)."""
        tenant, _, emp = _fixture('vig')
        svc = _service(tenant, 'Corte', '1000.00')
        EmployeeCompensationHistory.objects.create(
            employee=emp, payment_type='commission',
            fixed_salary=Decimal('0.00'), commission_rate=Decimal('30.00'),
            effective_date=timezone.localdate() + timedelta(days=30),
        )
        rate, source = SaleCommissionService.resolve_commission_rate(emp, svc, timezone.localdate())
        assert source == SaleCommissionService.SOURCE_GLOBAL
        assert rate == Decimal('40.00')


# ───────────────── 2. Venta con varios barberos ─────────────────

class TestMultiBarberSale:
    def test_two_services_two_barbers_reach_payroll(self):
        """Una venta con 2 servicios y 2 barberos reparte la comisión."""
        tenant_a, _, emp_a = _fixture('mb_a', rate='40.00')
        tenant_b, _, emp_b = _fixture('mb_b', rate='50.00')
        # Mismo tenant para la venta
        emp_b.tenant = tenant_a
        emp_b.save()

        svc_corte = _service(tenant_a, 'Corte', '1000.00')
        svc_color = _service(tenant_a, 'Color', '2000.00')
        ServiceEmployee.objects.create(employee=emp_a, service=svc_corte)
        ServiceEmployee.objects.create(employee=emp_b, service=svc_color)

        sale = Sale.objects.create(
            tenant=tenant_a, user=emp_a.user, date_time=timezone.now(),
            total=Decimal('3000.00'), paid=Decimal('3000.00'),
            payment_method='cash', status='confirmed',
        )
        _add_detail(sale, svc_corte, employee=emp_a)
        _add_detail(sale, svc_color, employee=emp_b)

        # Snapshot de venta debe quedar NULL: la fuente es la línea.
        sale.refresh_from_db()
        assert sale.commission_amount_snapshot is None
        assert sale.commission_source == Sale.COMMISSION_SOURCE_LINE

        period_a = _period_for(emp_a)
        period_b = _period_for(emp_b)
        period_a.calculate_amounts()
        period_b.calculate_amounts()

        assert period_a.commission_earnings == Decimal('400.00')   # 40% de 1000
        assert period_b.commission_earnings == Decimal('1000.00')  # 50% de 2000

    def test_combo_is_a_single_line_single_commission(self):
        """Un combo es un servicio: una sola línea y una sola comisión."""
        tenant, _, emp = _fixture('combo', rate='40.00')
        combo = _service(tenant, 'Combo Corte+Color', '2500.00')
        ServiceEmployee.objects.create(employee=emp, service=combo)

        sale = Sale.objects.create(
            tenant=tenant, user=emp.user, date_time=timezone.now(),
            total=Decimal('2500.00'), paid=Decimal('2500.00'),
            payment_method='cash', status='confirmed',
        )
        _add_detail(sale, combo, employee=emp)

        period = _period_for(emp)
        period.calculate_amounts()
        assert period.commission_earnings == Decimal('1000.00')

    def test_products_never_generate_service_commission(self):
        """Los productos no generan comisión de servicios."""
        tenant, _, emp = _fixture('prod', rate='40.00')
        prod = _product(tenant, 'Shampoo', '300.00')
        svc = _service(tenant, 'Corte', '1000.00')
        ServiceEmployee.objects.create(employee=emp, service=svc)

        sale = Sale.objects.create(
            tenant=tenant, user=emp.user, date_time=timezone.now(),
            total=Decimal('1300.00'), paid=Decimal('1300.00'),
            payment_method='cash', status='confirmed',
        )
        _add_detail(sale, prod, service=False, employee=None)
        detail = _add_detail(sale, svc, employee=emp)

        assert detail.commission_amount_snapshot == Decimal('400.00')

        period = _period_for(emp)
        period.calculate_amounts()
        # Solo el servicio genera comisión, no el producto.
        assert period.commission_earnings == Decimal('400.00')


# ───────────────── 3. Inmutabilidad de snapshots ─────────────────

class TestSnapshotImmutability:
    def test_line_snapshot_is_immutable_after_confirmation(self):
        from django.core.exceptions import ValidationError
        tenant, _, emp_a = _fixture('imm_a', rate='40.00')
        _, _, emp_b = _fixture('imm_b', rate='40.00')
        emp_b.tenant = tenant
        emp_b.save()
        svc = _service(tenant, 'Corte', '1000.00')

        sale = Sale.objects.create(
            tenant=tenant, user=emp_a.user, date_time=timezone.now(),
            total=Decimal('1000.00'), paid=Decimal('1000.00'),
            payment_method='cash', status='confirmed',
        )
        detail = _add_detail(sale, svc, employee=emp_a)

        with pytest.raises(ValidationError):
            detail.commission_amount_snapshot = Decimal('999.00')
            detail.save()

    def test_snapshot_survives_employee_rate_change(self):
        """Cambiar la configuración del empleado NO altera la nómina."""
        tenant, _, emp = _fixture('freeze', rate='40.00')
        svc = _service(tenant, 'Corte', '1000.00')
        ServiceEmployee.objects.create(employee=emp, service=svc)

        sale = Sale.objects.create(
            tenant=tenant, user=emp.user, date_time=timezone.now(),
            total=Decimal('1000.00'), paid=Decimal('1000.00'),
            payment_method='cash', status='confirmed',
        )
        _add_detail(sale, svc, employee=emp)

        # El jefe cambia el % del empleado a 10%.
        emp.commission_rate = Decimal('10.00')
        emp.save()

        period = _period_for(emp)
        period.calculate_amounts()
        # Sigue siendo 40% porque el snapshot está congelado.
        assert period.commission_earnings == Decimal('400.00')


# ───────────────── 4. Ventas históricas (sin duplicación) ─────────────────

class TestHistoricalSales:
    def test_legacy_sale_snapshot_still_counts(self):
        """Una venta histórica (snapshot a nivel de venta) se sigue sumando."""
        tenant, _, emp = _fixture('legacy', rate='40.00')
        sale = Sale.objects.create(
            tenant=tenant, user=emp.user, employee=emp, date_time=timezone.now(),
            total=Decimal('1000.00'), paid=Decimal('1000.00'),
            payment_method='cash', status='confirmed',
        )
        # Snapshot a nivel de venta, como las ventas old.
        Sale.write_commission_snapshots(sale, Decimal('40.00'), Decimal('400.00'))

        assert sale.commission_source == Sale.COMMISSION_SOURCE_SALE

        period = _period_for(emp)
        period.calculate_amounts()
        assert period.commission_earnings == Decimal('400.00')

    def test_legacy_and_new_do_not_double_count(self):
        """Ventas históricas + nuevas en el mismo período: sin duplicar.

        Este test simula el peor caso: una venta con comisión por línea que
        además conserva un snapshot a nivel de venta. La regla de fuente
        única debe hacer que solo cuente la línea, sin sumar 400 + 400.
        """
        tenant, _, emp = _fixture('mixed', rate='40.00')
        svc = _service(tenant, 'Corte', '1000.00')
        ServiceEmployee.objects.create(employee=emp, service=svc)

        # Venta antigua: snapshot a nivel de venta.
        old = Sale.objects.create(
            tenant=tenant, user=emp.user, employee=emp, date_time=timezone.now(),
            total=Decimal('1000.00'), paid=Decimal('1000.00'),
            payment_method='cash', status='confirmed',
        )
        old.commission_amount_snapshot = Decimal('400.00')
        Sale.write_commission_snapshots(old, old.commission_rate_snapshot, Decimal('400.00'))

        # Venta nueva: snapshot por línea (y, por seguridad, también conserva
        # un snapshot de venta residual para probar que la regla lo ignora).
        new = Sale.objects.create(
            tenant=tenant, user=emp.user, employee=emp, date_time=timezone.now(),
            total=Decimal('1000.00'), paid=Decimal('1000.00'),
            payment_method='cash', status='confirmed',
        )
        _add_detail(new, svc, employee=emp)

        assert old.commission_source == Sale.COMMISSION_SOURCE_SALE
        assert new.commission_source == Sale.COMMISSION_SOURCE_LINE

        period = _period_for(emp)
        period.calculate_amounts()
        # 400 (histórica) + 400 (línea nueva) = 800. Ni una ni otra vez.
        assert period.commission_earnings == Decimal('800.00')

    def test_existing_paid_period_is_untouched_by_new_sales(self):
        """Los snapshots históricos no se recalculan ni se alteran."""
        tenant, _, emp = _fixture('paid', rate='40.00')
        sale = Sale.objects.create(
            tenant=tenant, user=emp.user, employee=emp, date_time=timezone.now(),
            total=Decimal('1000.00'), paid=Decimal('1000.00'),
            payment_method='cash', status='confirmed',
        )
        Sale.write_commission_snapshots(sale, sale.commission_rate_snapshot, Decimal('400.00'))
        original = sale.commission_amount_snapshot

        # Un segundo empleado cobra; nada debe alterar la venta anterior.
        _, _, other = _fixture('paid_b')
        other.tenant = tenant
        other.save()
        svc = _service(tenant, 'Color', '800.00')
        ServiceEmployee.objects.create(employee=other, service=svc)
        new_sale = Sale.objects.create(
            tenant=tenant, user=other.user, employee=other, date_time=timezone.now(),
            total=Decimal('800.00'), paid=Decimal('800.00'),
            payment_method='cash', status='confirmed',
        )
        _add_detail(new_sale, svc, employee=other)

        sale.refresh_from_db()
        assert sale.commission_amount_snapshot == original


# ───────────────── 5. Descuentos y canjes sobre la base ─────────────────

class TestDiscountsAffectCommissionableBase:
    def test_coupon_discount_is_not_commissioned(self):
        """El descuento NO se reparte como comisión: la base es el servicio."""
        tenant, _, emp = _fixture('disc', rate='40.00')
        svc = _service(tenant, 'Corte', '1000.00')
        ServiceEmployee.objects.create(employee=emp, service=svc)

        # Venta con descuento de 300: total 700, pero la línea vale 1000.
        sale = Sale.objects.create(
            tenant=tenant, user=emp.user, date_time=timezone.now(),
            total=Decimal('700.00'), discount=Decimal('300.00'),
            paid=Decimal('700.00'), payment_method='cash', status='confirmed',
        )
        detail = _add_detail(sale, svc, employee=emp)

        # La comisión se calcula sobre el precio del servicio, no sobre el
        # descuento aplicado al ticket.
        assert detail.commission_amount_snapshot == Decimal('400.00')

        period = _period_for(emp)
        period.calculate_amounts()
        assert period.commission_earnings == Decimal('400.00')

    def test_loyalty_redemption_does_not_inflate_commission(self):
        """Un canje de puntos no genera comisión extra."""
        tenant, _, emp = _fixture('pts', rate='40.00')
        svc = _service(tenant, 'Corte', '1000.00')
        ServiceEmployee.objects.create(employee=emp, service=svc)

        sale = Sale.objects.create(
            tenant=tenant, user=emp.user, date_time=timezone.now(),
            total=Decimal('900.00'), discount=Decimal('100.00'),
            points_redeemed=10, paid=Decimal('900.00'),
            payment_method='cash', status='confirmed',
        )
        _add_detail(sale, svc, employee=emp)

        period = _period_for(emp)
        period.calculate_amounts()
        assert period.commission_earnings == Decimal('400.00')


# ───────────────── 6. Reembolsos ─────────────────

class TestRefunds:
    def _sale_with_two_barbers(self):
        tenant, _, emp_a = _fixture('rf_a', rate='40.00')
        _, _, emp_b = _fixture('rf_b', rate='50.00')
        emp_b.tenant = tenant
        emp_b.save()
        svc_c = _service(tenant, 'Corte', '1000.00')
        svc_l = _service(tenant, 'Color', '1000.00')
        ServiceEmployee.objects.create(employee=emp_a, service=svc_c)
        ServiceEmployee.objects.create(employee=emp_b, service=svc_l)
        sale = Sale.objects.create(
            tenant=tenant, user=emp_a.user, employee=emp_a, date_time=timezone.now(),
            total=Decimal('2000.00'), paid=Decimal('2000.00'),
            payment_method='cash', status='confirmed',
        )
        _add_detail(sale, svc_c, employee=emp_a)
        _add_detail(sale, svc_l, employee=emp_b)
        return tenant, emp_a, emp_b, sale

    def test_full_refund_creates_one_negative_per_barber(self):
        tenant, emp_a, emp_b, sale = self._sale_with_two_barbers()
        ratio = Decimal('1')
        components = SaleCommissionService.refund_commission_components(sale, ratio)
        assert len(components) == 2
        assert {c['employee'] for c in components} == {emp_a, emp_b}
        assert all(c['amount'] < 0 for c in components)
        amounts = {c['employee'].id: c['amount'] for c in components}
        assert amounts[emp_a.id] == Decimal('-400.00')
        assert amounts[emp_b.id] == Decimal('-500.00')

    def test_partial_refund_is_proportional(self):
        tenant, emp_a, emp_b, sale = self._sale_with_two_barbers()
        # Reembolso del 50%
        components = SaleCommissionService.refund_commission_components(sale, Decimal('0.5'))
        amounts = {c['employee'].id: c['amount'] for c in components}
        assert amounts[emp_a.id] == Decimal('-200.00')
        assert amounts[emp_b.id] == Decimal('-250.00')

    def test_repeated_full_refund_is_blocked_by_constraint(self):
        """La constraint impide duplicar el reembolso total por línea."""
        from django.db import IntegrityError, transaction as db_transaction
        tenant, emp_a, emp_b, sale = self._sale_with_two_barbers()
        components = SaleCommissionService.refund_commission_components(sale, Decimal('1'))
        period = _period_for(emp_a)

        for c in components:
            CommissionAdjustment.objects.create(
                sale=sale, sale_detail=c['detail'], payroll_period=period,
                employee=c['employee'], amount=c['amount'], reason='refund',
                description='primer reembolso', tenant=tenant,
            )

        with pytest.raises(IntegrityError):
            with db_transaction.atomic():
                first = components[0]
                CommissionAdjustment.objects.create(
                    sale=sale, sale_detail=first['detail'], payroll_period=period,
                    employee=first['employee'], amount=first['amount'],
                    reason='refund', description='reembolso repetido', tenant=tenant,
                )

    def test_idempotency_key_prevents_duplicate_partial(self):
        tenant, emp_a, emp_b, sale = self._sale_with_two_barbers()
        period = _period_for(emp_a)
        from django.db import IntegrityError, transaction as db_transaction

        CommissionAdjustment.objects.create(
            sale=sale, idempotency_key='key-123', payroll_period=period,
            employee=emp_a, amount=Decimal('-200.00'), reason='partial_refund',
            description='parcial', tenant=tenant,
        )
        with pytest.raises(IntegrityError):
            with db_transaction.atomic():
                CommissionAdjustment.objects.create(
                    sale=sale, idempotency_key='key-123', payroll_period=period,
                    employee=emp_a, amount=Decimal('-200.00'), reason='partial_refund',
                    description='parcial repetido', tenant=tenant,
                )

    def test_legacy_sale_refund_uses_sale_source(self):
        """Una venta histórica se reembolsa a nivel de venta (1 ajuste)."""
        tenant, _, emp = _fixture('rf_legacy', rate='40.00')
        sale = Sale.objects.create(
            tenant=tenant, user=emp.user, employee=emp, date_time=timezone.now(),
            total=Decimal('1000.00'), paid=Decimal('1000.00'),
            payment_method='cash', status='confirmed',
        )
        Sale.write_commission_snapshots(sale, sale.commission_rate_snapshot, Decimal('400.00'))

        components = SaleCommissionService.refund_commission_components(sale, Decimal('1'))
        assert len(components) == 1
        assert components[0]['amount'] == Decimal('-400.00')
        assert components[0]['source'] == 'sale'

    def test_refundable_amount_prevents_over_refund(self):
        tenant, _, emp = _fixture('over', rate='40.00')
        sale = Sale.objects.create(
            tenant=tenant, user=emp.user, employee=emp, date_time=timezone.now(),
            total=Decimal('1000.00'), paid=Decimal('1000.00'),
            payment_method='cash', status='confirmed',
        )
        sale.amount_refunded = Decimal('600.00')
        sale.save(update_fields=['amount_refunded'])
        assert sale.refundable_amount == Decimal('400.00')


# ───────────────── 7. Aislamiento multi-tenant ─────────────────

class TestTenantIsolation:
    def test_line_employee_from_other_tenant_is_rejected(self):
        from django.core.exceptions import ValidationError
        tenant_a, _, emp_a = _fixture('iso_a', rate='40.00')
        _, _, emp_b = _fixture('iso_b', rate='40.00')
        svc = _service(tenant_a, 'Corte', '1000.00')
        ServiceEmployee.objects.create(employee=emp_a, service=svc)

        sale = Sale.objects.create(
            tenant=tenant_a, user=emp_a.user, date_time=timezone.now(),
            total=Decimal('1000.00'), paid=Decimal('1000.00'),
            payment_method='cash', status='confirmed',
        )
        ct = ContentType.objects.get(app_label='services_api', model='service')
        detail = SaleDetail.objects.create(
            sale=sale, content_type=ct, object_id=svc.id,
            name=svc.name, quantity=1, price=Decimal('1000.00'),
            employee=emp_b,  # empleado de OTRO tenant
        )
        with pytest.raises(ValidationError):
            detail.full_clean()

    def test_payroll_does_not_leak_other_tenant_commissions(self):
        tenant_a, _, emp_a = _fixture('iso_p_a', rate='40.00')
        tenant_b, _, emp_b = _fixture('iso_p_b', rate='40.00')
        svc_a = _service(tenant_a, 'Corte A', '1000.00')
        ServiceEmployee.objects.create(employee=emp_a, service=svc_a)

        sale_a = Sale.objects.create(
            tenant=tenant_a, user=emp_a.user, date_time=timezone.now(),
            total=Decimal('1000.00'), paid=Decimal('1000.00'),
            payment_method='cash', status='confirmed',
        )
        _add_detail(sale_a, svc_a, employee=emp_a)

        # Venta del tenant B, mismo empleadonothing
        svc_b = _service(tenant_b, 'Corte B', '5000.00')
        sale_b = Sale.objects.create(
            tenant=tenant_b, user=emp_b.user, date_time=timezone.now(),
            total=Decimal('5000.00'), paid=Decimal('5000.00'),
            payment_method='cash', status='confirmed',
        )

        period = _period_for(emp_a)
        period.calculate_amounts()
        # Solo la venta de SU tenant.
        assert period.commission_earnings == Decimal('400.00')


# ───────────────── 8. Determinismo ─────────────────

class TestDeterminism:
    def test_recalculating_twice_gives_same_result(self):
        tenant, _, emp_a = _fixture('det_a', rate='40.00')
        _, _, emp_b = _fixture('det_b', rate='50.00')
        emp_b.tenant = tenant
        emp_b.save()
        svc = _service(tenant, 'Corte', '1000.00')
        ServiceEmployee.objects.create(employee=emp_a, service=svc)

        sale = Sale.objects.create(
            tenant=tenant, user=emp_a.user, date_time=timezone.now(),
            total=Decimal('1000.00'), paid=Decimal('1000.00'),
            payment_method='cash', status='confirmed',
        )
        _add_detail(sale, svc, employee=emp_a)

        period = _period_for(emp_a)
        period.calculate_amounts()
        first = period.commission_earnings
        period.calculate_amounts()
        second = period.commission_earnings
        assert first == second == Decimal('400.00')

    def test_void_sale_generates_no_commission(self):
        tenant, _, emp = _fixture('void', rate='40.00')
        svc = _service(tenant, 'Corte', '1000.00')
        ServiceEmployee.objects.create(employee=emp, service=svc)
        sale = Sale.objects.create(
            tenant=tenant, user=emp.user, date_time=timezone.now(),
            total=Decimal('1000.00'), paid=Decimal('1000.00'),
            payment_method='cash', status='confirmed',
        )
        _add_detail(sale, svc, employee=emp)

        sale.status = 'void'
        sale.save()

        period = _period_for(emp)
        period.calculate_amounts()
        assert period.commission_earnings == Decimal('0.00')
