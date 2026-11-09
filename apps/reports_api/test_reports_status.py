import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.tenants_api.models import Tenant
from apps.pos_api.models import Sale, CashRegister
from apps.subscriptions_api.models import SubscriptionPlan
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


@pytest.mark.django_db
class TestReportsStatusFiltering(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(name='basic', price=0, is_active=True, is_public=True, features={'reports': True})
        self.tenant = Tenant.objects.create(name='T', subdomain='tr', subscription_plan=plan, is_active=True)
        self.user = User.objects.create_user(email='r@t.com', password='p', full_name='R', tenant=self.tenant, is_email_verified=True)
        # grant permission
        from django.contrib.auth.models import Permission
        from apps.roles_api.models import Role, UserRole
        from django.contrib.contenttypes.models import ContentType
        role, _ = Role.objects.get_or_create(name='Client-Admin', defaults={'scope': 'TENANT'})
        ct = ContentType.objects.get(app_label='reports_api', model='reportpermission')
        for cn in ['view_sales_reports', 'view_employee_reports', 'view_kpi_dashboard']:
            perm, _ = Permission.objects.get_or_create(codename=cn, content_type=ct, defaults={'name': cn})
            role.permissions.add(perm)
        UserRole.objects.get_or_create(user=self.user, role=role, tenant=self.tenant)
        self.client = APIClient()
        from rest_framework_simplejwt.tokens import AccessToken
        t = AccessToken.for_user(self.user)
        t['tenant_id'] = self.user.tenant_id
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(t)}")
        self.client.cookies['access_token'] = str(t)

        # Create sales in different statuses
        Sale.objects.create(tenant=self.tenant, total=Decimal('100.00'), status='confirmed', date_time=timezone.now())
        Sale.objects.create(tenant=self.tenant, total=Decimal('50.00'), status='draft', date_time=timezone.now())
        Sale.objects.create(tenant=self.tenant, total=Decimal('30.00'), status='void', date_time=timezone.now())
        Sale.objects.create(tenant=self.tenant, total=Decimal('200.00'), status='refunded', amount_refunded=Decimal('200.00'), date_time=timezone.now())

    def test_sales_report_excludes_void_and_draft(self):
        from django.urls import reverse
        r = self.client.get(reverse('sales-report'))
        assert r.status_code == 200
        # Only confirmed sale (100) should count; refunded (200) excluded
        assert r.data['total_sales'] == 100.0

    def test_sales_report_includes_refunded_amount(self):
        from django.urls import reverse
        r = self.client.get(reverse('sales-report'))
        assert r.status_code == 200
        assert r.data['refunded_amount'] == 200.0
        assert r.data['refunded_count'] == 1

    def test_dashboard_stats_excludes_void_and_draft(self):
        from django.urls import reverse
        r = self.client.get(reverse('dashboard-stats'))
        assert r.status_code == 200
        assert r.data['monthly_revenue'] == 100.0

    def test_kpi_excludes_void_and_draft(self):
        from django.urls import reverse
        r = self.client.get(reverse('kpi-dashboard'))
        assert r.status_code == 200
        assert r.data['monthly']['revenue'] == 100.0