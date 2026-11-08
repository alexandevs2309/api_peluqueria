from decimal import Decimal
from datetime import date
import pytest
from django.test import TestCase
from apps.tenants_api.models import Tenant
from apps.auth_api.models import User
from apps.employees_api.models import Employee, PayrollPeriod
from apps.employees_api.earnings_models import RegaliaPascual
from apps.subscriptions_api.models import SubscriptionPlan


@pytest.mark.django_db
class TestRegaliaPascual(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(name='basic', price=10, is_active=True, is_public=True)
        self.tenant = Tenant.objects.create(name='T', subdomain='tr', subscription_plan=plan, is_active=True)
        self.user = User.objects.create_user(email='r@t.com', password='p', full_name='R', tenant=self.tenant, is_email_verified=True)
        self.emp = Employee.objects.create(user=self.user, tenant=self.tenant, payment_type='fixed', fixed_salary=Decimal('50000.00'), is_active=True)
        # Create periods for the year
        for m in range(1, 13):
            from calendar import monthrange
            start = date(2026, m, 1)
            end = date(2026, m, monthrange(2026, m)[1])
            pp = PayrollPeriod.objects.create(employee=self.emp, period_type='monthly', period_start=start, period_end=end, status='open')
            pp.calculate_amounts()
            pp.save()

    def test_regalia_calculated(self):
        reg = RegaliaPascual.calculate_for_employee(self.emp, 2026)
        assert reg.amount > 0
        assert reg.is_tax_exempt is True
        # 50000 * 12 / 12 = 50000
        assert reg.amount == Decimal('50000.00')

    def test_regalia_cap(self):
        # minimum salary 23223, cap 5x = 116115
        self.emp.fixed_salary = Decimal('200000.00')
        self.emp.save()
        # recalc periods
        for p in PayrollPeriod.objects.filter(employee=self.emp):
            p.calculate_amounts()
            p.save()
        reg = RegaliaPascual.calculate_for_employee(self.emp, 2026)
        assert reg.amount <= Decimal('116115.00')

    def test_regalia_proportional(self):
        # Employee started in April (9 months) - simulate by deleting Jan-Mar periods
        PayrollPeriod.objects.filter(employee=self.emp, period_start__month__in=[1,2,3]).delete()
        reg = RegaliaPascual.calculate_for_employee(self.emp, 2026)
        # 9 months of 50000 = 450000 / 12 = 37500
        assert reg.amount == Decimal('37500.00')

    def test_regalia_unique(self):
        r1 = RegaliaPascual.calculate_for_employee(self.emp, 2026)
        r2 = RegaliaPascual.calculate_for_employee(self.emp, 2026)
        assert r1.id == r2.id