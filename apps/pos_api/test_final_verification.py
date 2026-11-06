"""Verificación final Sprint 2.1: refresh, ventas y audit log."""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from apps.tenants_api.models import Tenant
from apps.pos_api.models import Sale, CashRegister
from apps.settings_api.models import Branch
from apps.roles_api.models import Role, UserRole
from apps.audit_api.models import AuditLog

User = get_user_model()


def _grant_role(user, tenant, role_name):
    from apps.roles_api.default_permissions import ensure_role_default_permissions
    role = Role.objects.get(name=role_name)
    ensure_role_default_permissions(role)
    UserRole.objects.get_or_create(user=user, role=role, tenant=tenant)


class FinalRefreshTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='T', subdomain='t-final', is_active=True)
        self.user = User.objects.create_user(
            email='final@example.com', password='FinalPass123!', full_name='Final',
            tenant=self.tenant, is_email_verified=True,
        )
        self.client = APIClient()
        login = self.client.post('/api/auth/cookie-login/', {
            'email': 'final@example.com', 'password': 'FinalPass123!',
        }, format='json')
        self.assertEqual(login.status_code, 200)
        self.refresh = login.cookies.get('refresh_token').value
        # atributos de cookie
        self.access_cookie = login.cookies.get('access_token')
        self.refresh_cookie = login.cookies.get('refresh_token')

    def test_cookie_attributes(self):
        for c in (self.access_cookie, self.refresh_cookie):
            self.assertTrue(c['httponly'])
            self.assertIn(c['samesite'].lower(), ('lax', 'none'))
            # Secure depende de DEBUG; en tests DEBUG=True => False
            self.assertFalse(c['secure'])

    def test_simultaneous_refresh_one_succeeds(self):
        c1 = APIClient()
        c2 = APIClient()
        c1.cookies['refresh_token'] = self.refresh
        c2.cookies['refresh_token'] = self.refresh

        r1 = c1.post('/api/auth/cookie-refresh/', {}, format='json')
        r2 = c2.post('/api/auth/cookie-refresh/', {}, format='json')

        # Al menos uno debe tener éxito; el otro debe ser 401 por blacklist
        statuses = sorted([r1.status_code, r2.status_code])
        self.assertEqual(statuses, [200, 401])


class FinalSalesAccessTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='T2', subdomain='t2-final', is_active=True)
        # plan con feature cash_register
        from apps.subscriptions_api.models import SubscriptionPlan
        plan, _ = SubscriptionPlan.objects.get_or_create(
            name='basic', defaults={'price': 0, 'max_users': 10, 'max_employees': 10,
                                    'features': {'cash_register': True, 'pos': True}}
        )
        plan.features = {'cash_register': True, 'pos': True, 'multi_location': True}
        plan.allows_multiple_branches = True
        plan.save(update_fields=['features', 'allows_multiple_branches'])
        self.tenant.subscription_plan = plan
        self.tenant.save(update_fields=['subscription_plan'])
        self.admin = User.objects.create_user(
            email='admin2@example.com', password='pass', full_name='Admin2',
            tenant=self.tenant, is_email_verified=True,
        )
        self.cajera = User.objects.create_user(
            email='cajera@example.com', password='pass', full_name='Cajera',
            tenant=self.tenant, is_email_verified=True,
        )
        self.estilista = User.objects.create_user(
            email='estilista@example.com', password='pass', full_name='Estilista',
            tenant=self.tenant, is_email_verified=True,
        )
        _grant_role(self.admin, self.tenant, 'Client-Admin')
        _grant_role(self.cajera, self.tenant, 'Cajera')
        _grant_role(self.estilista, self.tenant, 'Estilista')

        self.branch = Branch.objects.create(tenant=self.tenant, name='Sucursal 1', is_main=True, is_active=True)

        # Venta creada por admin
        self.sale_admin = Sale.objects.create(tenant=self.tenant, total=100, status='confirmed',
                                             created_by=self.admin, user=self.admin, branch=self.branch)
        # Venta creada por cajera
        self.sale_cajera = Sale.objects.create(tenant=self.tenant, total=50, status='confirmed',
                                              created_by=self.cajera, user=self.cajera, branch=self.branch)

        self.client = APIClient()

    def _auth(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        from rest_framework_simplejwt.tokens import AccessToken
        t = AccessToken.for_user(user)
        t['tenant_id'] = user.tenant_id
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {str(t)}")
        c.cookies['access_token'] = str(t)
        return c

    def test_admin_sees_all_sales(self):
        c = self._auth(self.admin)
        r = c.get('/api/pos/sales/')
        self.assertEqual(r.status_code, 200)
        ids = {x['id'] for x in r.data.get('results', r.data)}
        self.assertIn(self.sale_admin.id, ids)
        self.assertIn(self.sale_cajera.id, ids)

    def test_cajera_sees_only_own_sales(self):
        c = self._auth(self.cajera)
        r = c.get('/api/pos/sales/')
        self.assertEqual(r.status_code, 200)
        ids = {x['id'] for x in r.data.get('results', r.data)}
        self.assertIn(self.sale_cajera.id, ids)
        self.assertNotIn(self.sale_admin.id, ids)

    def test_estilista_sees_only_own_sales(self):
        c = self._auth(self.estilista)
        r = c.get('/api/pos/sales/')
        self.assertEqual(r.status_code, 200)
        ids = {x['id'] for x in r.data.get('results', r.data)}
        self.assertNotIn(self.sale_admin.id, ids)

    def test_branch_filter(self):
        branch2 = Branch.objects.create(tenant=self.tenant, name='Sucursal 2', is_main=False, is_active=True)
        sale2 = Sale.objects.create(tenant=self.tenant, total=75, status='confirmed',
                                    created_by=self.admin, user=self.admin, branch=branch2)
        c = self._auth(self.admin)
        r = c.get(f'/api/pos/sales/?branch_id={self.branch.id}')
        self.assertEqual(r.status_code, 200)
        ids = {x['id'] for x in r.data.get('results', r.data)}
        self.assertIn(self.sale_admin.id, ids)
        self.assertNotIn(sale2.id, ids)


class FinalAuditLogTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name='T3', subdomain='t3-final', is_active=True)
        self.superuser = User.objects.create_superuser(
            email='superfinal@example.com', password='pass', full_name='Super'
        )
        self.normal = User.objects.create_user(
            email='normal@example.com', password='pass', full_name='Normal',
            tenant=self.tenant, is_email_verified=True,
        )
        _grant_role(self.normal, self.tenant, 'Client-Admin')

        # Log con tenant
        self.log_with = AuditLog.objects.create(
            tenant=self.tenant, user=self.normal, action='VIEW', source='test', description='con tenant'
        )
        # Log sin tenant (evento huérfano)
        self.log_without = AuditLog.objects.create(
            tenant=None, user=None, action='VIEW', source='test', description='sin tenant'
        )

    def test_normal_user_does_not_see_other_tenant_logs(self):
        c = APIClient()
        c.force_authenticate(user=self.normal)
        from rest_framework_simplejwt.tokens import AccessToken
        t = AccessToken.for_user(self.normal)
        t['tenant_id'] = self.normal.tenant_id
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {str(t)}")
        c.cookies['access_token'] = str(t)
        r = c.get('/api/audit/logs/')
        self.assertEqual(r.status_code, 200)
        ids = {x['id'] for x in r.data.get('results', r.data)}
        self.assertIn(self.log_with.id, ids)
        self.assertNotIn(self.log_without.id, ids)

    def test_superuser_can_query_logs_without_tenant(self):
        c = APIClient()
        c.force_authenticate(user=self.superuser)
        r = c.get('/api/audit/logs/')
        self.assertEqual(r.status_code, 200)
        # SuperAdmin ve todos (incluye sin tenant)
        ids = {x['id'] for x in r.data.get('results', r.data)}
        self.assertIn(self.log_without.id, ids)
