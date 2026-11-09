import pytest
from django.test import TestCase
from apps.tenants_api.models import Tenant
from apps.auth_api.models import User
from apps.appointments_api.models import Appointment
from apps.clients_api.models import Client
from apps.employees_api.models import Employee
from apps.services_api.models import Service
from apps.subscriptions_api.models import SubscriptionPlan
from datetime import timedelta
from django.utils import timezone


@pytest.mark.django_db
class TestAppointmentFilters(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(name='basic', price=10, is_active=True, is_public=True, features={'appointments': True})
        self.tenant = Tenant.objects.create(name='T', subdomain='taf', subscription_plan=plan, is_active=True)
        self.user = User.objects.create_user(email='u@t.com', password='p', full_name='U', tenant=self.tenant, is_email_verified=True)
        # grant permission
        from django.contrib.auth.models import Permission
        from apps.roles_api.models import Role, UserRole
        from django.contrib.contenttypes.models import ContentType
        role, _ = Role.objects.get_or_create(name='Client-Admin', defaults={'scope': 'TENANT'})
        ct = ContentType.objects.get(app_label='appointments_api', model='appointment')
        perm, _ = Permission.objects.get_or_create(codename='view_appointment', content_type=ct, defaults={'name': 'view'})
        role.permissions.add(perm)
        # also change/create
        for cn in ['add_appointment', 'change_appointment']:
            p, _ = Permission.objects.get_or_create(codename=cn, content_type=ct, defaults={'name': cn})
            role.permissions.add(p)
        UserRole.objects.get_or_create(user=self.user, role=role, tenant=self.tenant)
        self.client_obj = Client.objects.create(tenant=self.tenant, full_name='Client', created_by=self.user)
        self.emp = Employee.objects.create(user=self.user, tenant=self.tenant, is_active=True)
        self.service = Service.objects.create(tenant=self.tenant, name='Corte', price=100, duration=30)
        # Create appointments
        now = timezone.now()
        # Align to 30-min slot
        aligned = now.replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
        Appointment.objects.create(tenant=self.tenant, client=self.client_obj, stylist=self.user, service=self.service, date_time=aligned, status='scheduled')
        Appointment.objects.create(tenant=self.tenant, client=self.client_obj, stylist=self.user, service=self.service, date_time=aligned + timedelta(days=1), status='completed')
        Appointment.objects.create(tenant=self.tenant, client=self.client_obj, stylist=self.user, service=self.service, date_time=aligned + timedelta(days=2), status='cancelled')

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

    def test_filter_by_status(self):
        c = self._auth(self.user)
        r = c.get('/api/appointments/appointments/?status=completed')
        assert r.status_code == 200
        results = r.data.get('results', r.data)
        assert all(a['status'] == 'completed' for a in results)
        assert len(results) == 1

    def test_filter_by_stylist(self):
        c = self._auth(self.user)
        r = c.get(f'/api/appointments/appointments/?stylist={self.user.id}')
        assert r.status_code == 200
        results = r.data.get('results', r.data)
        assert len(results) == 3

    def test_client_conflict_blocked(self):
        """Un cliente no puede tener dos citas solapadas con distintos estilistas."""
        from apps.auth_api.models import User as U
        user2 = U.objects.create_user(email='u2@t.com', password='p', full_name='U2', tenant=self.tenant, is_email_verified=True)
        from apps.employees_api.models import Employee
        Employee.objects.create(user=user2, tenant=self.tenant, is_active=True)
        # Try to create a second appointment for the same client at the same time with different stylist
        # Use the same time as the first appointment to force a conflict
        first_apt = Appointment.objects.filter(tenant=self.tenant, status='scheduled').first()
        r = self._auth(self.user).post('/api/appointments/appointments/', {
            'client': self.client_obj.id,
            'stylist': user2.id,
            'service': self.service.id,
            'date_time': first_apt.date_time.isoformat(),
        }, format='json')
        assert r.status_code == 400
        assert 'programada' in str(r.data).lower()

    def test_pagination(self):
        c = self._auth(self.user)
        r = c.get('/api/appointments/appointments/?limit=2&offset=0')
        assert r.status_code == 200
        assert 'count' in r.data
        assert r.data['count'] == 3
        assert len(r.data['results']) == 2
        r2 = c.get('/api/appointments/appointments/?limit=2&offset=2')
        assert r2.status_code == 200
        assert len(r2.data['results']) == 1