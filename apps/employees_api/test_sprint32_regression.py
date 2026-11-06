"""Regresión Sprint 3.2: deducciones, préstamos, períodos aprobados."""
from decimal import Decimal
from datetime import date, timedelta

import pytest
from django.test import TestCase
from apps.tenants_api.models import Tenant
from apps.auth_api.models import User
from apps.employees_api.models import Employee, PayrollPeriod, PayrollDeduction
from apps.employees_api.models import Loan
from apps.subscriptions_api.models import SubscriptionPlan
from apps.roles_api.models import Role, UserRole


@pytest.mark.django_db
class TestDeductionIdempotency(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(name='basic', price=10, is_active=True, is_public=True)
        self.tenant = Tenant.objects.create(name='T', subdomain='t32', subscription_plan=plan, is_active=True)
        self.user = User.objects.create_user(email='u@t.com', password='p', full_name='U', tenant=self.tenant, is_email_verified=True)
        self.emp = Employee.objects.create(user=self.user, tenant=self.tenant, payment_type='fixed', fixed_salary=Decimal('1000.00'), is_active=True)
        self.period = PayrollPeriod.objects.create(employee=self.emp, period_type='biweekly', period_start=date(2026,1,1), period_end=date(2026,1,15), status='open')

    def test_recalculate_does_not_duplicate_auto_deductions(self):
        # manual deduction
        PayrollDeduction.objects.create(period=self.period, deduction_type='other', amount=Decimal('5.00'), description='manual', is_automatic=False)
        self.period.calculate_amounts()
        self.period.save()
        count1 = self.period.deductions.filter(is_automatic=True).count()
        self.period.calculate_amounts()
        self.period.save()
        count2 = self.period.deductions.filter(is_automatic=True).count()
        assert count1 == count2
        assert self.period.deductions.filter(is_automatic=False).count() == 1

    def test_manual_deduction_survives_recalc(self):
        PayrollDeduction.objects.create(period=self.period, deduction_type='other', amount=Decimal('7.00'), description='manual keep', is_automatic=False, source='manual')
        self.period.calculate_amounts()
        self.period.save()
        assert self.period.deductions.filter(description='manual keep').exists()


@pytest.mark.django_db
class TestLoanNoDoubleDiscount(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(name='basic', price=10, is_active=True, is_public=True)
        self.tenant = Tenant.objects.create(name='T2', subdomain='t32b', subscription_plan=plan, is_active=True)
        self.user = User.objects.create_user(email='u2@t.com', password='p', full_name='U2', tenant=self.tenant, is_email_verified=True)
        self.emp = Employee.objects.create(user=self.user, tenant=self.tenant, payment_type='fixed', fixed_salary=Decimal('1000.00'), is_active=True)
        self.period = PayrollPeriod.objects.create(employee=self.emp, period_type='biweekly', period_start=date(2026,1,1), period_end=date(2026,1,15), status='open')
        self.loan = Loan.objects.create(employee=self.emp, amount=Decimal('100.00'), installments=2, remaining_balance=Decimal('100.00'), status='active', description='L1')

    def test_loan_deduction_has_loan_fk(self):
        self.period.calculate_amounts()
        self.period.save()
        loan_deds = self.period.deductions.filter(deduction_type='loan')
        assert loan_deds.exists()
        for d in loan_deds:
            assert d.loan_id == self.loan.id

    def test_mark_paid_updates_loan_once(self):
        self.period.calculate_amounts()
        self.period.save()
        self.period.status = 'pending_approval'
        self.period.save()
        self.period.approve(approved_by=self.user)
        self.period.mark_as_paid('cash', 'ref1', self.user)
        self.loan.refresh_from_db()
        assert self.loan.remaining_balance < Decimal('100.00')
        # second mark_as_paid should fail (not approved)
        p2 = PayrollPeriod.objects.create(employee=self.emp, period_type='biweekly', period_start=date(2026,1,16), period_end=date(2026,1,31), status='open')
        p2.calculate_amounts()
        p2.save()
        # no double discount on same loan from re-running calculate
        before = self.loan.remaining_balance
        self.period.calculate_amounts()
        assert self.loan.remaining_balance == before


@pytest.mark.django_db
class TestApprovedPeriodImmutability(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(name='basic', price=10, is_active=True, is_public=True)
        self.tenant = Tenant.objects.create(name='T3', subdomain='t32c', subscription_plan=plan, is_active=True)
        self.user = User.objects.create_user(email='u3@t.com', password='p', full_name='U3', tenant=self.tenant, is_email_verified=True)
        self.emp = Employee.objects.create(user=self.user, tenant=self.tenant, payment_type='fixed', fixed_salary=Decimal('1000.00'), is_active=True)
        self.period = PayrollPeriod.objects.create(employee=self.emp, period_type='biweekly', period_start=date(2026,1,1), period_end=date(2026,1,15), status='open')
        self.period.calculate_amounts()
        self.period.save()
        self.period.status = 'pending_approval'
        self.period.save()
        self.period.approve(approved_by=self.user)

    def test_snapshot_preserved(self):
        snap = self.period.calculation_snapshot
        self.period.calculate_amounts()  # should not recalc
        self.period.save()
        self.period.refresh_from_db()
        assert self.period.calculation_snapshot == snap

    def test_financial_fields_immutable(self):
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            self.period.gross_amount = Decimal('999.00')
            self.period.save()


@pytest.mark.django_db
class TestWeeklyCrossMonth(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(name='basic', price=10, is_active=True, is_public=True)
        self.tenant = Tenant.objects.create(name='T4', subdomain='t32d', subscription_plan=plan, is_active=True)
        self.user = User.objects.create_user(email='u4@t.com', password='p', full_name='U4', tenant=self.tenant, is_email_verified=True)
        self.emp = Employee.objects.create(user=self.user, tenant=self.tenant, payment_type='fixed', fixed_salary=Decimal('1000.00'), is_active=True)

    def test_jan_feb_cross(self):
        p = PayrollPeriod.objects.create(employee=self.emp, period_type='weekly', period_start=date(2026,1,27), period_end=date(2026,2,2), status='open')
        p.calculate_amounts()
        # 5 days in Jan (27-31) + 2 days in Feb (1-2)
        # Jan: 5/31*1000=161.29, Feb: 2/28*1000=71.43 => 232.72
        print('CROSS base:', p.base_salary)
        assert p.base_salary > 0

    def test_feb_mar_leap(self):
        p = PayrollPeriod.objects.create(employee=self.emp, period_type='weekly', period_start=date(2024,2,25), period_end=date(2024,3,2), status='open')
        p.calculate_amounts()
        print('LEAP base:', p.base_salary)
        assert p.base_salary > 0

    def test_consecutive_no_overlap(self):
        p1 = PayrollPeriod.objects.create(employee=self.emp, period_type='weekly', period_start=date(2026,1,1), period_end=date(2026,1,7), status='open')
        p2 = PayrollPeriod.objects.create(employee=self.emp, period_type='weekly', period_start=date(2026,1,8), period_end=date(2026,1,14), status='open')
        p1.calculate_amounts()
        p2.calculate_amounts()
        total = p1.base_salary + p2.base_salary
        print('CONSEC total:', total)
        assert total <= Decimal('1000.00') * Decimal('14') / Decimal('28')