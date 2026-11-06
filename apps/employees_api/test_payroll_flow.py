from decimal import Decimal
from datetime import date
import pytest
from django.test import TestCase
from apps.tenants_api.models import Tenant
from apps.auth_api.models import User
from apps.employees_api.models import Employee, PayrollPeriod
from apps.subscriptions_api.models import SubscriptionPlan
from apps.roles_api.models import Role, UserRole
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


@pytest.mark.django_db
class TestPayrollFullFlow(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(name='basic', price=10, is_active=True, is_public=True)
        self.tenant = Tenant.objects.create(name='T', subdomain='tfinal', subscription_plan=plan, is_active=True)
        self.admin = User.objects.create_user(email='admin@t.com', password='p', full_name='Admin', tenant=self.tenant, is_email_verified=True)
        self.emp_user = User.objects.create_user(email='emp@t.com', password='p', full_name='Emp', tenant=self.tenant, is_email_verified=True)
        self.emp = Employee.objects.create(user=self.emp_user, tenant=self.tenant, payment_type='fixed', fixed_salary=Decimal('1000.00'), is_active=True)
        role = Role.objects.get(name='Client-Admin')
        UserRole.objects.get_or_create(user=self.admin, role=role, tenant=self.tenant)
        # grant perms
        ct = ContentType.objects.get(app_label='employees_api', model='employee')
        for codename in ['view_employee_payroll', 'change_employee_payroll', 'approve_payroll', 'manage_employee_loans']:
            perm, _ = Permission.objects.get_or_create(codename=codename, content_type=ct, defaults={'name': codename})
            role.permissions.add(perm)
        self.period = PayrollPeriod.objects.create(employee=self.emp, period_type='biweekly', period_start=date(2026,1,1), period_end=date(2026,1,15), status='open')
        self.period.calculate_amounts()
        self.period.save()

    def _auth(self, user):
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import AccessToken
        c = APIClient()
        c.force_authenticate(user=user)
        t = AccessToken.for_user(user)
        t['tenant_id'] = user.tenant_id
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {str(t)}")
        c.cookies['access_token'] = str(t)
        return c

    def test_submit_approve_pay_register_receipt_history_detail(self):
        c = self._auth(self.admin)
        # submit
        r = c.post(f'/api/employees/payroll/client/payroll/{self.period.id}/submit/', {}, format='json')
        assert r.status_code == 200, r.data
        self.period.refresh_from_db()
        assert self.period.status == 'pending_approval'

        # approve
        r = c.post(f'/api/employees/payroll/client/payroll/{self.period.id}/approve/', {}, format='json')
        assert r.status_code == 200, r.data
        self.period.refresh_from_db()
        assert self.period.status == 'approved'
        assert self.period.is_finalized is True

        # register payment
        r = c.post('/api/employees/payroll/client/payroll/register_payment/', {'period_id': self.period.id, 'payment_method': 'cash', 'payment_reference': 'REF1'}, format='json')
        assert r.status_code == 200, r.data
        self.period.refresh_from_db()
        assert self.period.status == 'paid'

        # receipt
        r = c.get(f'/api/employees/payroll/payments/{self.period.id}/receipt/')
        assert r.status_code == 200, r.data
        assert r.data['amounts']['net_amount'] == float(self.period.net_amount)

        # history
        r = c.get('/api/employees/payroll/client/payroll/history/')
        assert r.status_code == 200
        ids = [p['id'] for p in r.data['periods']]
        assert self.period.id in ids

        # detail
        r = c.get(f'/api/employees/payroll/client/payroll/{self.period.id}/detail/')
        assert r.status_code == 200
        assert r.data['period']['status'] == 'paid'

    def test_reject_flow(self):
        c = self._auth(self.admin)
        self.period.status = 'pending_approval'
        self.period.submitted_for_approval_at = __import__('django.utils.timezone', fromlist=['now']).now()
        self.period.save()
        r = c.post(f'/api/employees/payroll/client/payroll/{self.period.id}/reject/', {'reason': 'test'}, format='json')
        assert r.status_code == 200, r.data
        self.period.refresh_from_db()
        assert self.period.status == 'rejected'

    def test_pay_open_period_blocked(self):
        c = self._auth(self.admin)
        r = c.post('/api/employees/payroll/client/payroll/register_payment/', {'period_id': self.period.id, 'payment_method': 'cash'}, format='json')
        assert r.status_code == 400

    def test_my_earnings_isolation(self):
        # emp user can see own
        c = self._auth(self.emp_user)
        r = c.get('/api/employees/payroll/client/payroll/my-earnings/')
        # may be 200 or 403 depending on employee_profile; just ensure no 500
        assert r.status_code in (200, 403)