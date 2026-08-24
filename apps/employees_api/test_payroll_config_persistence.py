"""
Tests críticos para payroll config persistence y list_periods.
Cubre el bug REPORTADO: PUT /employees/{id}/payroll_config/ retorna 200
pero el valor no persiste.
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.auth_api.factories import UserFactory
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollPeriod, PayrollConfiguration
from apps.pos_api.models import Sale
from apps.roles_api.models import Role, UserRole
from apps.subscriptions_api.models import SubscriptionPlan
from apps.tenants_api.models import Tenant

User = get_user_model()


def _make_plan():
    plan, _ = SubscriptionPlan.objects.get_or_create(
        name='basic',
        defaults={
            'description': 'Plan base test',
            'price': 0,
            'duration_month': 1,
            'max_employees': 50,
            'max_users': 50,
            'is_active': True,
            'features': {'payroll': True},
        }
    )
    return plan


def _make_tenant(name='Tenant', subdomain='tenant'):
    owner = User.objects.create_superuser(
        email=f'{subdomain}-owner@test.com', password='pass', full_name=f'{name} Owner'
    )
    plan = _make_plan()
    tenant = Tenant.objects.create(
        name=name, subdomain=subdomain, owner=owner,
        subscription_plan=plan, subscription_status='active', is_active=True,
    )
    return tenant, owner


def _make_admin(tenant):
    user = User.objects.create_user(
        email=f'admin-{tenant.subdomain}@test.com', password='pass',
        full_name='Admin', tenant=tenant, is_email_verified=True,
    )
    role, _ = Role.objects.get_or_create(
        name='Client-Admin',
        defaults={'scope': 'TENANT', 'description': 'Admin'}
    )
    ct, _ = ContentType.objects.get_or_create(app_label='employees_api', model='employee')
    perms = Permission.objects.filter(content_type__app_label='employees_api')
    role.permissions.add(*perms)
    UserRole.objects.create(user=user, role=role, tenant=tenant)
    return user


def _make_employee(tenant, email='emp@test.com', **kwargs):
    user = User.objects.create_user(
        email=email, password='pass', full_name='Employee', tenant=tenant,
        is_email_verified=True,
    )
    defaults = {
        'user': user,
        'tenant': tenant,
        'profession': 'stylist',
        'payment_type': 'mixed',
        'fixed_salary': Decimal('9000.00'),
        'commission_rate': Decimal('40.00'),
    }
    defaults.update(kwargs)
    return Employee.objects.create(**defaults)


def _auth_client(user, tenant):
    client = APIClient()
    token = AccessToken.for_user(user)
    token['tenant_id'] = tenant.id
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token)}')
    client.force_authenticate(user=user)
    return client


# ==============================================================================
# PAYROLL CONFIG — SAVE & PERSISTENCE
# ==============================================================================

@pytest.mark.django_db
class TestPayrollConfigPersistence:
    """
    Bug report: PUT /employees/{id}/payroll_config/ retorna 200 pero valor no persiste.
    Estos tests verifican que el guardado realmente persiste en DB.
    """

    def _setup(self):
        tenant, owner = _make_tenant('Config Test', 'config')
        admin = _make_admin(tenant)
        employee = _make_employee(tenant, 'emp-config@test.com')
        return tenant, admin, employee

    def test_put_fixed_salary_persists(self):
        """PUT fixed_salary → GET must return updated value"""
        tenant, admin, employee = self._setup()
        client = _auth_client(admin, tenant)

        # Update fixed_salary from 9000 to 20000
        url = reverse('employee-payroll-config', kwargs={'pk': employee.id})
        response = client.put(url, {
            'fixed_salary': '20000.00',
        }, format='json')

        assert response.status_code == 200, f"PUT failed: {response.data}"

        # Verify the value persisted in the response
        assert response.data['fixed_salary'] == 20000.0, \
            f"Response fixed_salary={response.data['fixed_salary']}, expected 20000.0"

        # CRITICAL: Verify it persists in DB via GET
        get_response = client.get(url)
        assert get_response.status_code == 200
        assert get_response.data['fixed_salary'] == 20000.0, \
            f"GET after PUT: fixed_salary={get_response.data['fixed_salary']}, expected 20000.0"

        # CRITICAL: Verify it persists in DB via direct model query
        employee.refresh_from_db()
        assert employee.fixed_salary == Decimal('20000.00'), \
            f"DB value: fixed_salary={employee.fixed_salary}, expected 20000.00"

    def test_put_all_fields_persists(self):
        """PUT all payroll config fields → all must persist"""
        tenant, admin, employee = self._setup()
        client = _auth_client(admin, tenant)

        url = reverse('employee-payroll-config', kwargs={'pk': employee.id})
        response = client.put(url, {
            'payment_type': 'fixed',
            'fixed_salary': '15000.00',
            'commission_rate': '25.00',
        }, format='json')

        assert response.status_code == 200

        employee.refresh_from_db()
        assert employee.payment_type == 'fixed', f"payment_type={employee.payment_type}"
        assert employee.fixed_salary == Decimal('15000.00'), f"fixed_salary={employee.fixed_salary}"
        assert employee.commission_rate == Decimal('25.00'), f"commission_rate={employee.commission_rate}"

    def test_put_creates_compensation_history(self):
        """PUT must create EmployeeCompensationHistory entry"""
        tenant, admin, employee = self._setup()
        client = _auth_client(admin, tenant)

        url = reverse('employee-payroll-config', kwargs={'pk': employee.id})
        response = client.put(url, {
            'fixed_salary': '12000.00',
        }, format='json')

        assert response.status_code == 200

        from apps.employees_api.compensation_models import EmployeeCompensationHistory
        history = EmployeeCompensationHistory.objects.filter(employee=employee).latest('id')
        assert history.fixed_salary == Decimal('12000.00')
        assert history.created_by == admin

    def test_get_returns_current_values(self):
        """GET returns current employee payroll config values"""
        tenant, admin, employee = self._setup()
        client = _auth_client(admin, tenant)

        url = reverse('employee-payroll-config', kwargs={'pk': employee.id})
        response = client.get(url)

        assert response.status_code == 200
        assert response.data['payment_type'] == 'mixed'
        assert response.data['fixed_salary'] == 9000.0
        assert response.data['commission_rate'] == 40.0

    def test_put_invalid_payment_type_returns_400(self):
        """PUT with invalid payment_type returns 400"""
        tenant, admin, employee = self._setup()
        client = _auth_client(admin, tenant)

        url = reverse('employee-payroll-config', kwargs={'pk': employee.id})
        response = client.put(url, {
            'payment_type': 'invalid_type',
        }, format='json')

        assert response.status_code == 400

    def test_put_preserves_other_fields(self):
        """PUT only fixed_salary must not affect payment_type"""
        tenant, admin, employee = self._setup()
        client = _auth_client(admin, tenant)

        url = reverse('employee-payroll-config', kwargs={'pk': employee.id})
        response = client.put(url, {
            'fixed_salary': '18000.00',
        }, format='json')

        assert response.status_code == 200

        employee.refresh_from_db()
        assert employee.payment_type == 'mixed'  # unchanged
        assert employee.fixed_salary == Decimal('18000.00')
        assert employee.commission_rate == Decimal('40.00')  # unchanged

    def test_multiple_updates_persist_latest(self):
        """Multiple PUTs → last value persists"""
        tenant, admin, employee = self._setup()
        client = _auth_client(admin, tenant)

        url = reverse('employee-payroll-config', kwargs={'pk': employee.id})

        # First update
        client.put(url, {'fixed_salary': '12000.00'}, format='json')
        # Second update (the one that should persist)
        response = client.put(url, {'fixed_salary': '20000.00'}, format='json')
        assert response.status_code == 200

        # Third update
        client.put(url, {'fixed_salary': '15000.00'}, format='json')

        # Verify last value
        employee.refresh_from_db()
        assert employee.fixed_salary == Decimal('15000.00')

        get_response = client.get(url)
        assert get_response.data['fixed_salary'] == 15000.0


# ==============================================================================
# LIST PERIODS — WAS 500, NOW MUST RETURN 200
# ==============================================================================

@pytest.mark.django_db
class TestListPeriodsEndpoint:
    """
    list_periods was returning 500 due to profession_display AttributeError.
    Also tests that sales aggregation is per-period, not global.
    """

    def _setup(self):
        tenant, owner = _make_tenant('Period Test', 'period')
        admin = _make_admin(tenant)
        employee = _make_employee(tenant, 'emp-period@test.com')
        return tenant, admin, employee

    def test_list_periods_returns_200(self):
        """GET /payroll/client/payroll/ must return 200"""
        tenant, admin, employee = self._setup()
        client = _auth_client(admin, tenant)

        response = client.get(reverse('payroll-list-periods'))
        assert response.status_code == 200, f"list_periods returned {response.status_code}"

    def test_list_periods_returns_periods_list(self):
        """Response must have 'periods' key with list"""
        tenant, admin, employee = self._setup()
        client = _auth_client(admin, tenant)

        response = client.get(reverse('payroll-list-periods'))
        data = response.json()

        assert 'periods' in data
        assert isinstance(data['periods'], list)
        assert len(data['periods']) >= 1

    def test_list_periods_includes_employee_data(self):
        """Each period must include employee_name, employee_profession, etc."""
        tenant, admin, employee = self._setup()
        client = _auth_client(admin, tenant)

        response = client.get(reverse('payroll-list-periods'))
        periods = response.json()['periods']

        for period in periods:
            assert 'employee_name' in period
            assert 'employee_profession' in period
            assert 'employee_payment_type' in period
            assert 'employee_commission_rate' in period
            assert 'base_salary' in period
            assert 'net_amount' in period
            assert 'period_start' in period
            assert 'period_end' in period
            assert 'status' in period

    def test_list_periods_profession_display_is_string(self):
        """employee_profession must be a human-readable string (not None/error)"""
        tenant, admin, employee = self._setup()
        client = _auth_client(admin, tenant)

        response = client.get(reverse('payroll-list-periods'))
        periods = response.json()['periods']

        for period in periods:
            profession = period['employee_profession']
            assert isinstance(profession, str), f"profession is {type(profession)}: {profession}"
            assert profession != '', f"profession is empty"

    def test_list_periods_sales_aggregated_per_period(self):
        """Sales must be aggregated per period with correct period scope"""
        tenant, admin, employee = self._setup()
        client = _auth_client(admin, tenant)

        today = timezone.localdate()

        # Create the current period (what list_periods would create)
        if today.day <= 15:
            start_date = today.replace(day=1)
            end_date = today.replace(day=15)
        else:
            start_date = today.replace(day=16)
            end_date = today.replace(day=monthrange(today.year, today.month)[1])

        period = PayrollPeriod.objects.create(
            employee=employee, period_type='biweekly',
            period_start=start_date,
            period_end=end_date,
            status='open',
        )

        # Sale INSIDE current period range
        sale_in = Sale.objects.create(
            employee=employee, tenant=tenant, user=admin,
            date_time=timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time()) + timedelta(days=2)),
            total=Decimal('100.00'), paid=Decimal('100.00'),
            payment_method='cash', status='confirmed',
        )

        # Sale OUTSIDE current period range (different month)
        other_month = start_date.replace(day=1) - timedelta(days=1)
        sale_out = Sale.objects.create(
            employee=employee, tenant=tenant, user=admin,
            date_time=timezone.make_aware(timezone.datetime.combine(other_month, timezone.datetime.min.time())),
            total=Decimal('200.00'), paid=Decimal('200.00'),
            payment_method='cash', status='confirmed',
        )

        response = client.get(reverse('payroll-list-periods'))
        periods = response.json()['periods']

        # Only one period returned (the current one)
        my_period = next((p for p in periods if p['id'] == period.id), None)
        assert my_period is not None, "Current period not found in response"

        # Current period should only have sale_in's total (100), NOT sale_out's (200)
        assert my_period['gross_sales'] == 100.0, \
            f"gross_sales={my_period['gross_sales']}, expected 100.0"
        assert my_period['services_count'] == 1

    def test_list_periods_no_duplicate_periods(self):
        """Must not create duplicate periods for same employee"""
        tenant, admin, employee = self._setup()
        client = _auth_client(admin, tenant)

        # Call list_periods twice
        client.get(reverse('payroll-list-periods'))
        client.get(reverse('payroll-list-periods'))

        today = timezone.localdate()
        if today.day <= 15:
            start_date = today.replace(day=1)
            end_date = today.replace(day=15)
        else:
            start_date = today.replace(day=16)
            end_date = today.replace(day=monthrange(today.year, today.month)[1])

        count = PayrollPeriod.objects.filter(
            employee=employee,
            period_start=start_date,
            period_end=end_date,
        ).count()
        assert count == 1, f"Found {count} periods for same employee+dates, expected 1"

    def test_list_periods_empty_tenant(self):
        """Tenant with no employees returns empty periods list"""
        tenant, owner = _make_tenant('Empty Tenant', 'empty-period')
        admin = _make_admin(tenant)
        client = _auth_client(admin, tenant)

        response = client.get(reverse('payroll-list-periods'))
        assert response.status_code == 200
        assert response.json()['periods'] == []


from calendar import monthrange


# ==============================================================================
# END-TO-END: SAVE CONFIG → VERIFY PERIOD CALCULATES WITH NEW VALUE
# ==============================================================================

@pytest.mark.django_db
class TestPayrollConfigEndToEnd:
    """Integration test: save config → period recalculates with new fixed_salary"""

    def _setup(self):
        tenant, owner = _make_tenant('E2E Test', 'e2e')
        admin = _make_admin(tenant)
        employee = _make_employee(tenant, 'emp-e2e@test.com')
        return tenant, admin, employee

    def _ensure_period(self, employee):
        today = timezone.localdate()
        if today.day <= 15:
            start_date = today.replace(day=1)
            end_date = today.replace(day=15)
        else:
            start_date = today.replace(day=16)
            end_date = today.replace(day=monthrange(today.year, today.month)[1])
        period, _ = PayrollPeriod.objects.get_or_create(
            employee=employee,
            period_start=start_date,
            period_end=end_date,
            defaults={'period_type': 'biweekly', 'status': 'open'},
        )
        return period, start_date, end_date

    def test_save_config_then_period_uses_new_salary(self):
        """After updating fixed_salary, new period should use updated value"""
        tenant, admin, employee = self._setup()
        client = _auth_client(admin, tenant)

        # Update fixed_salary from 9000 to 20000
        url = reverse('employee-payroll-config', kwargs={'pk': employee.id})
        response = client.put(url, {'fixed_salary': '20000.00'}, format='json')
        assert response.status_code == 200

        # Refresh employee
        employee.refresh_from_db()
        assert employee.fixed_salary == Decimal('20000.00')

        # Create period directly in DB
        period, start_date, end_date = self._ensure_period(employee)

        # Sync snapshot (like list_periods does)
        PayrollPeriod.objects.filter(pk=period.pk).update(
            fixed_salary_snapshot=employee.fixed_salary,
            commission_rate_snapshot=employee.commission_rate,
            payment_type_snapshot=employee.payment_type,
        )
        period.refresh_from_db()
        period.calculate_amounts()
        period.save()

        expected_base = Decimal('20000.00') / 2
        assert period.base_salary == expected_base, \
            f"base_salary={period.base_salary}, expected {expected_base}"

    def test_list_periods_reflects_new_salary(self):
        """list_periods response shows updated base_salary after config save"""
        tenant, admin, employee = self._setup()
        client = _auth_client(admin, tenant)

        # Create period directly
        period, start_date, end_date = self._ensure_period(employee)

        # Update salary
        url = reverse('employee-payroll-config', kwargs={'pk': employee.id})
        client.put(url, {'fixed_salary': '20000.00'}, format='json')
        employee.refresh_from_db()

        # Sync snapshots (like list_periods does)
        PayrollPeriod.objects.filter(pk=period.pk).update(
            fixed_salary_snapshot=employee.fixed_salary,
            commission_rate_snapshot=employee.commission_rate,
            payment_type_snapshot=employee.payment_type,
        )
        period.refresh_from_db()
        period.calculate_amounts()
        period.save(update_fields=[
            'base_salary', 'commission_earnings', 'gross_amount',
            'deductions_total', 'net_amount', 'can_pay', 'pay_block_reason',
        ])

        # Now list_periods should show the updated base_salary
        response = client.get(reverse('payroll-list-periods'))
        periods = response.json()['periods']
        my_period = next((p for p in periods if p['id'] == period.id), None)

        assert my_period is not None
        assert my_period['base_salary'] == 10000.0, \
            f"list_periods base_salary={my_period['base_salary']}, expected 10000.0"
