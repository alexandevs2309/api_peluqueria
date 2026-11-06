from decimal import Decimal
from datetime import date
import pytest
from django.test import TestCase
from apps.tenants_api.models import Tenant
from apps.auth_api.models import User
from apps.employees_api.models import Employee, PayrollPeriod
from apps.subscriptions_api.models import SubscriptionPlan


@pytest.mark.django_db
class TestPeriodDetail(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(name='basic', price=10, is_active=True, is_public=True)
        self.tenant = Tenant.objects.create(name='T', subdomain='td', subscription_plan=plan, is_active=True)
        self.user = User.objects.create_user(email='d@t.com', password='p', full_name='D', tenant=self.tenant, is_email_verified=True)
        from django.contrib.auth.models import Permission
        from apps.roles_api.models import Role, UserRole
        role, _ = Role.objects.get_or_create(name='Client-Admin', defaults={'scope': 'TENANT'})
        perm = Permission.objects.get_or_create(codename='view_employee_payroll', content_type__app_label='employees_api',
            defaults={'name': 'Can view payroll', 'content_type': __import__('django.contrib.contenttypes.models', fromlist=['ContentType']).ContentType.objects.get(app_label='employees_api', model='employee')})[0]
        role.permissions.add(perm)
        UserRole.objects.get_or_create(user=self.user, role=role, tenant=self.tenant)
        self.emp = Employee.objects.create(user=self.user, tenant=self.tenant, payment_type='fixed', fixed_salary=Decimal('1000.00'), is_active=True)
        self.period = PayrollPeriod.objects.create(employee=self.emp, period_type='biweekly', period_start=date(2026,1,1), period_end=date(2026,1,15), status='open')
        self.period.calculate_amounts()
        self.period.save()

    def test_period_detail_returns_breakdown(self):
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import AccessToken
        c = APIClient()
        c.force_authenticate(user=self.user)
        t = AccessToken.for_user(self.user)
        t['tenant_id'] = self.user.tenant_id
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {str(t)}")
        c.cookies['access_token'] = str(t)
        r = c.get(f'/api/employees/payroll/client/payroll/{self.period.id}/detail/')
        assert r.status_code == 200
        assert r.data['period_id'] == self.period.id
        assert 'amounts' in r.data
        assert 'services' in r.data
        assert 'deductions' in r.data

    def test_period_detail_cross_tenant_blocked(self):
        plan2 = SubscriptionPlan.objects.create(name='basic2', price=10, is_active=True, is_public=True)
        tenant2 = Tenant.objects.create(name='T2', subdomain='td2', subscription_plan=plan2, is_active=True)
        user2 = User.objects.create_user(email='d2@t.com', password='p', full_name='D2', tenant=tenant2, is_email_verified=True)
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import AccessToken
        c = APIClient()
        c.force_authenticate(user=user2)
        t = AccessToken.for_user(user2)
        t['tenant_id'] = user2.tenant_id
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {str(t)}")
        c.cookies['access_token'] = str(t)
        r = c.get(f'/api/employees/payroll/client/payroll/{self.period.id}/detail/')
        assert r.status_code in (403, 404)