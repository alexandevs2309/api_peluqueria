import pytest
from decimal import Decimal
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollPeriod
from apps.tenants_api.models import Tenant
from apps.roles_api.models import Role, UserRole
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestEnsurePeriod:
    """ensure-period: garantiza un período abierto actual para un empleado sin período"""

    def _client(self, user, tenant):
        client = APIClient()
        token = AccessToken.for_user(user)
        token['tenant_id'] = tenant.id
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token)}')
        return client

    def _make_admin(self, email, tenant):
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        admin = User.objects.create_user(email=email, password='pass', tenant=tenant)
        role, _ = Role.objects.get_or_create(
            name='Client-Admin',
            defaults={'scope': 'TENANT', 'description': 'Client admin test role'}
        )
        perms = Permission.objects.filter(content_type__app_label='employees_api')
        ct, _ = ContentType.objects.get_or_create(app_label='employees_api', model='employee')
        for codename, name in [
            ('approve_payroll', 'Can approve payroll periods'),
            ('change_employee_payroll', 'Can recalculate and submit payroll periods'),
        ]:
            perm, _ = Permission.objects.get_or_create(codename=codename, content_type=ct, defaults={'name': name})
            perms |= Permission.objects.filter(pk=perm.pk)
        role.permissions.add(*perms)
        UserRole.objects.create(user=admin, role=role, tenant=tenant)
        return admin

    def _setup(self):
        owner = User.objects.create_superuser(email='owner-ens@test.com', password='pass', full_name='Owner')
        tenant = Tenant.objects.create(name='Tenant', subdomain='tenant-ensure-period', owner=owner)
        admin = self._make_admin('admin@test.com', tenant)
        emp_user = User.objects.create_user(email='emp@test.com', password='pass', tenant=tenant)
        employee = Employee.objects.create(
            user=emp_user,
            tenant=tenant,
            payment_type='commission',
            commission_rate=Decimal('10.00'),
            fixed_salary=Decimal('0.00'),
        )
        return admin, tenant, employee

    def test_creates_current_open_period_for_employee_without_one(self):
        admin, tenant, employee = self._setup()
        client = self._client(admin, tenant)
        resp = client.post(reverse('payroll-ensure-period'), {'employee_id': employee.id}, format='json')
        assert resp.status_code == 200, resp.content
        data = resp.json()
        assert data['created'] is True
        assert data['status'] == 'open'
        assert data['id'] > 0

        period = PayrollPeriod.objects.get(id=data['id'])
        assert period.employee_id == employee.id
        assert period.status == 'open'
        assert period.period_type == 'biweekly'
        today = timezone.localdate()
        assert period.period_start <= today <= period.period_end

    def test_is_idempotent(self):
        admin, tenant, employee = self._setup()
        client = self._client(admin, tenant)
        url = reverse('payroll-ensure-period')
        first = client.post(url, {'employee_id': employee.id}, format='json').json()
        second = client.post(url, {'employee_id': employee.id}, format='json').json()
        assert second['id'] == first['id']
        assert second['created'] is False
        assert PayrollPeriod.objects.filter(employee=employee).count() == 1

    def test_missing_employee_id_returns_400(self):
        admin, tenant, _ = self._setup()
        client = self._client(admin, tenant)
        resp = client.post(reverse('payroll-ensure-period'), {}, format='json')
        assert resp.status_code == 400

    def test_employee_from_other_tenant_not_found(self):
        admin, tenant, employee = self._setup()
        other_owner = User.objects.create_superuser(email='owner2@test.com', password='pass', full_name='O2')
        other_tenant = Tenant.objects.create(name='Other', subdomain='other-ensure', owner=other_owner)
        other_admin = self._make_admin('other-admin@test.com', other_tenant)
        client = self._client(other_admin, other_tenant)
        resp = client.post(reverse('payroll-ensure-period'), {'employee_id': employee.id}, format='json')
        assert resp.status_code == 404

    def test_non_admin_cannot_create_period(self):
        admin, tenant, employee = self._setup()
        staff = User.objects.create_user(email='staff@test.com', password='pass', tenant=tenant)
        client = self._client(staff, tenant)
        resp = client.post(reverse('payroll-ensure-period'), {'employee_id': employee.id}, format='json')
        assert resp.status_code == 403
