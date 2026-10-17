from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
import pytest

from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollPeriod
from apps.pos_api.models import Sale
from apps.tenants_api.models import Tenant
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestPayrollCommissions:
    def test_commission_calculated_from_confirmed_sales_with_snapshots(self):
        owner = User.objects.create_superuser(email='owner_c1@test.com', password='pass', full_name='O1')
        tenant = Tenant.objects.create(name="T1", subdomain='t1', owner=owner)
        user = User.objects.create_user(email="emp_c1@test.com", password="test123", tenant=tenant)
        employee = Employee.objects.create(
            user=user,
            tenant=tenant,
            payment_type='commission',
            commission_rate=Decimal('40.00'),
            fixed_salary=Decimal('0.00')
        )

        today = timezone.localdate()
        period = PayrollPeriod.objects.create(
            employee=employee,
            period_type='biweekly',
            period_start=today.replace(day=16) if today.day > 15 else today.replace(day=1),
            period_end=today.replace(day=31) if today.day > 15 else today.replace(day=15),
            status='open',
        )

        sale = Sale.objects.create(
            employee=employee,
            tenant=tenant,
            user=user,
            date_time=timezone.now(),
            total=Decimal('100.00'),
            paid=Decimal('100.00'),
            payment_method='cash',
            status='confirmed'
        )
        assert sale.commission_amount_snapshot == Decimal('40.00')
        assert sale.commission_rate_snapshot == Decimal('40.00')

        period.calculate_amounts()
        assert period.commission_earnings == Decimal('40.00')
        assert period.gross_amount == Decimal('40.00')

    def test_void_sales_do_not_contribute_commission(self):
        owner = User.objects.create_superuser(email='owner_c2@test.com', password='pass', full_name='O2')
        tenant = Tenant.objects.create(name="T2", subdomain='t2', owner=owner)
        user = User.objects.create_user(email="emp_c2@test.com", password="test123", tenant=tenant)
        employee = Employee.objects.create(
            user=user,
            tenant=tenant,
            payment_type='commission',
            commission_rate=Decimal('40.00'),
            fixed_salary=Decimal('0.00')
        )

        today = timezone.localdate()
        period = PayrollPeriod.objects.create(
            employee=employee,
            period_type='biweekly',
            period_start=today.replace(day=16) if today.day > 15 else today.replace(day=1),
            period_end=today.replace(day=31) if today.day > 15 else today.replace(day=15),
            status='open',
        )

        Sale.objects.create(
            employee=employee,
            tenant=tenant,
            user=user,
            date_time=timezone.now(),
            total=Decimal('100.00'),
            paid=Decimal('100.00'),
            payment_method='cash',
            status='void'
        )
        period.calculate_amounts()
        assert period.commission_earnings == Decimal('0.00')

    def test_mixed_employee_gets_base_and_commission(self):
        owner = User.objects.create_superuser(email='owner_c3@test.com', password='pass', full_name='O3')
        tenant = Tenant.objects.create(name="T3", subdomain='t3', owner=owner)
        user = User.objects.create_user(email="emp_c3@test.com", password="test123", tenant=tenant)
        employee = Employee.objects.create(
            user=user,
            tenant=tenant,
            payment_type='mixed',
            commission_rate=Decimal('40.00'),
            fixed_salary=Decimal('2000.00')
        )

        today = timezone.localdate()
        period = PayrollPeriod.objects.create(
            employee=employee,
            period_type='biweekly',
            period_start=today.replace(day=16) if today.day > 15 else today.replace(day=1),
            period_end=today.replace(day=31) if today.day > 15 else today.replace(day=15),
            status='open',
        )

        Sale.objects.create(
            employee=employee,
            tenant=tenant,
            user=user,
            date_time=timezone.now(),
            total=Decimal('100.00'),
            paid=Decimal('100.00'),
            payment_method='cash',
            status='confirmed'
        )
        period.calculate_amounts()
        assert period.commission_earnings == Decimal('40.00')
        assert period.base_salary == Decimal('1000.00')  # biweekly
        assert period.gross_amount == Decimal('1040.00')

    def test_sale_with_null_snapshot_does_not_contribute(self):
        """Ventas sin snapshot de comisión (históricas) no deben sumar comisión."""
        owner = User.objects.create_superuser(email='owner_c5@test.com', password='pass', full_name='O5')
        tenant = Tenant.objects.create(name="T5", subdomain='t5', owner=owner)
        user = User.objects.create_user(email="emp_c5@test.com", password="test123", tenant=tenant)
        employee = Employee.objects.create(
            user=user, tenant=tenant, payment_type='commission',
            commission_rate=Decimal('40.00'), fixed_salary=Decimal('0.00')
        )
        today = timezone.localdate()
        period = PayrollPeriod.objects.create(
            employee=employee, period_type='biweekly',
            period_start=today.replace(day=16) if today.day > 15 else today.replace(day=1),
            period_end=today.replace(day=31) if today.day > 15 else today.replace(day=15),
            status='open',
        )
        sale = Sale.objects.create(
            employee=employee, tenant=tenant, user=user, date_time=timezone.now(),
            total=Decimal('100.00'), paid=Decimal('100.00'), payment_method='cash',
            status='confirmed'
        )
        # Simular venta histórica sin snapshot (bypass del save) — solo para el test
        Sale.objects.filter(pk=sale.pk).update(commission_amount_snapshot=None)

        period.calculate_amounts()
        assert period.commission_earnings == Decimal('0.00')

    def test_sale_from_wrong_tenant_is_excluded(self):
        """Ventas de otro tenant no deben sumar a la nómina."""
        owner = User.objects.create_superuser(email='owner_c6@test.com', password='pass', full_name='O6')
        tenant = Tenant.objects.create(name="T6", subdomain='t6', owner=owner)
        other_tenant = Tenant.objects.create(name="T6b", subdomain='t6b', owner=owner)
        user = User.objects.create_user(email="emp_c6@test.com", password="test123", tenant=tenant)
        employee = Employee.objects.create(
            user=user, tenant=tenant, payment_type='commission',
            commission_rate=Decimal('40.00'), fixed_salary=Decimal('0.00')
        )
        today = timezone.localdate()
        period = PayrollPeriod.objects.create(
            employee=employee, period_type='biweekly',
            period_start=today.replace(day=16) if today.day > 15 else today.replace(day=1),
            period_end=today.replace(day=31) if today.day > 15 else today.replace(day=15),
            status='open',
        )
        # Venta con tenant incorrecto sobre el mismo empleado
        Sale.objects.create(
            employee=employee, tenant=other_tenant, user=user, date_time=timezone.now(),
            total=Decimal('100.00'), paid=Decimal('100.00'), payment_method='cash',
            status='confirmed'
        )
        period.calculate_amounts()
        assert period.commission_earnings == Decimal('0.00')

    def test_sale_outside_period_is_excluded(self):
        """Ventas fuera del rango de fechas no deben sumar."""
        owner = User.objects.create_superuser(email='owner_c7@test.com', password='pass', full_name='O7')
        tenant = Tenant.objects.create(name="T7", subdomain='t7', owner=owner)
        user = User.objects.create_user(email="emp_c7@test.com", password="test123", tenant=tenant)
        employee = Employee.objects.create(
            user=user, tenant=tenant, payment_type='commission',
            commission_rate=Decimal('40.00'), fixed_salary=Decimal('0.00')
        )
        today = timezone.localdate()
        period = PayrollPeriod.objects.create(
            employee=employee, period_type='biweekly',
            period_start=today.replace(day=16) if today.day > 15 else today.replace(day=1),
            period_end=today.replace(day=31) if today.day > 15 else today.replace(day=15),
            status='open',
        )
        # Venta 60 días antes (fuera del período)
        Sale.objects.create(
            employee=employee, tenant=tenant, user=user,
            date_time=timezone.now() - timedelta(days=60),
            total=Decimal('100.00'), paid=Decimal('100.00'), payment_method='cash',
            status='confirmed'
        )
        period.calculate_amounts()
        assert period.commission_earnings == Decimal('0.00')

    def test_fixed_employee_commission_only_adjustments(self):
        owner = User.objects.create_superuser(email='owner_c4@test.com', password='pass', full_name='O4')
        tenant = Tenant.objects.create(name="T4", subdomain='t4', owner=owner)
        user = User.objects.create_user(email="emp_c4@test.com", password="test123", tenant=tenant)
        employee = Employee.objects.create(
            user=user,
            tenant=tenant,
            payment_type='fixed',
            commission_rate=Decimal('40.00'),
            fixed_salary=Decimal('2000.00')
        )

        today = timezone.localdate()
        period = PayrollPeriod.objects.create(
            employee=employee,
            period_type='biweekly',
            period_start=today.replace(day=16) if today.day > 15 else today.replace(day=1),
            period_end=today.replace(day=31) if today.day > 15 else today.replace(day=15),
            status='open',
        )

        Sale.objects.create(
            employee=employee,
            tenant=tenant,
            user=user,
            date_time=timezone.now(),
            total=Decimal('100.00'),
            paid=Decimal('100.00'),
            payment_method='cash',
            status='confirmed'
        )
        period.calculate_amounts()
        # fixed solo ajustes; comisiones de ventas no se suman
        assert period.commission_earnings == Decimal('0.00')
        assert period.base_salary == Decimal('1000.00')
