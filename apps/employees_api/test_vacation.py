from decimal import Decimal
from datetime import date
import pytest
from django.test import TestCase
from apps.tenants_api.models import Tenant
from apps.auth_api.models import User
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import Vacation
from apps.subscriptions_api.models import SubscriptionPlan


@pytest.mark.django_db
class TestVacation(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(name='basic', price=10, is_active=True, is_public=True)
        self.tenant = Tenant.objects.create(name='T', subdomain='tv', subscription_plan=plan, is_active=True)
        self.user = User.objects.create_user(email='v@t.com', password='p', full_name='V', tenant=self.tenant, is_email_verified=True)
        # hire_date 2 years ago
        from datetime import timedelta
        self.emp = Employee.objects.create(user=self.user, tenant=self.tenant, payment_type='fixed', fixed_salary=Decimal('1000.00'), is_active=True, hire_date=date(2024,1,1))

    def test_vacation_1_year(self):
        from apps.auth_api.models import User as U
        u2 = U.objects.create_user(email='v2@t.com', password='p', full_name='V2', tenant=self.tenant, is_email_verified=True)
        emp2 = Employee.objects.create(user=u2, tenant=self.tenant, payment_type='fixed', fixed_salary=Decimal('1000.00'), is_active=True, hire_date=date(2025,1,1))
        vac = Vacation.calculate_for_employee(emp2, 2026)
        assert vac.days_entitled == 14

    def test_vacation_5_years(self):
        from apps.auth_api.models import User as U
        u3 = U.objects.create_user(email='v3@t.com', password='p', full_name='V3', tenant=self.tenant, is_email_verified=True)
        emp3 = Employee.objects.create(user=u3, tenant=self.tenant, payment_type='fixed', fixed_salary=Decimal('1000.00'), is_active=True, hire_date=date(2020,1,1))
        vac = Vacation.calculate_for_employee(emp3, 2026)
        assert vac.days_entitled == 18

    def test_vacation_proportional(self):
        from apps.auth_api.models import User as U
        u4 = U.objects.create_user(email='v4@t.com', password='p', full_name='V4', tenant=self.tenant, is_email_verified=True)
        emp4 = Employee.objects.create(user=u4, tenant=self.tenant, payment_type='fixed', fixed_salary=Decimal('1000.00'), is_active=True, hire_date=date(2026,6,1))
        vac = Vacation.calculate_for_employee(emp4, 2026)
        # 7 months worked (>6) → 7 days
        assert vac.days_entitled == 7

    def test_vacation_paid_amount(self):
        from apps.auth_api.models import User as U
        u5 = U.objects.create_user(email='v5@t.com', password='p', full_name='V5', tenant=self.tenant, is_email_verified=True)
        emp5 = Employee.objects.create(user=u5, tenant=self.tenant, payment_type='fixed', fixed_salary=Decimal('1000.00'), is_active=True, hire_date=date(2025,1,1))
        vac = Vacation.calculate_for_employee(emp5, 2026)
        daily = Decimal('1000.00') / Decimal('23.83')
        expected = (daily * 14).quantize(Decimal('0.01'))
        assert vac.paid_amount == expected

    def test_vacation_enjoyed(self):
        vac = Vacation.calculate_for_employee(self.emp, 2026)
        vac.mark_enjoyed(date(2026,7,1), date(2026,7,14))
        assert vac.status == 'enjoyed'
        assert vac.days_taken == 14

    def test_vacation_fraction_minimum_week(self):
        vac = Vacation.calculate_for_employee(self.emp, 2026)
        import pytest
        with pytest.raises(ValueError):
            vac.mark_enjoyed(date(2026,7,1), date(2026,7,3))

    def test_vacation_compensate_restricted(self):
        vac = Vacation.calculate_for_employee(self.emp, 2026)
        admin = User.objects.create_superuser(email='admin2@t.com', password='p', full_name='Admin2')
        import pytest
        with pytest.raises(ValueError):
            vac.compensate(admin, termination_type='despido_causa')
        # allowed
        vac2 = Vacation.calculate_for_employee(self.emp, 2026) if False else vac
        vac.compensate(admin, termination_type='desahucio')
        assert vac.status == 'compensated'
        assert vac.termination_type == 'desahucio'

    def test_vacation_commission_employee(self):
        from apps.auth_api.models import User as U
        u = U.objects.create_user(email='vc@t.com', password='p', full_name='VC', tenant=self.tenant, is_email_verified=True)
        emp = Employee.objects.create(user=u, tenant=self.tenant, payment_type='commission', commission_rate=Decimal('10.00'), fixed_salary=Decimal('0.00'), is_active=True, hire_date=date(2025,1,1))
        # create a period with gross to test average
        from apps.employees_api.models import PayrollPeriod
        pp = PayrollPeriod.objects.create(employee=emp, period_type='monthly', period_start=date(2026,1,1), period_end=date(2026,1,31), status='open', payment_type_snapshot='commission', commission_rate_snapshot=Decimal('10.00'))
        pp.commission_earnings = Decimal('500.00')
        pp.gross_amount = Decimal('500.00')
        pp.save()
        vac = Vacation.calculate_for_employee(emp, 2026)
        assert vac.paid_amount > 0

    def test_vacation_payroll_period_link(self):
        vac = Vacation.calculate_for_employee(self.emp, 2026)
        from apps.employees_api.models import PayrollPeriod
        pp = PayrollPeriod.objects.create(employee=self.emp, period_type='biweekly', period_start=date(2026,7,1), period_end=date(2026,7,15), status='open')
        admin = User.objects.create_superuser(email='admin3@t.com', password='p', full_name='Admin3')
        vac.compensate(admin, termination_type='desahucio', payroll_period=pp)
        vac.refresh_from_db()
        assert vac.payroll_period_id == pp.id

    def test_vacation_unique(self):
        v1 = Vacation.calculate_for_employee(self.emp, 2026)
        v2 = Vacation.calculate_for_employee(self.emp, 2026)
        assert v1.id == v2.id