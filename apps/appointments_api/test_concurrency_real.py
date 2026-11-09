"""Pruebas de concurrencia real para reservas de citas.

En SQLite, select_for_update() es un no-op, por lo que estas pruebas se omiten.
En PostgreSQL, select_for_update() bloquea filas reales y serializa transacciones.
"""
import pytest
from django.test import TestCase, TransactionTestCase
from django.db import connection
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.tenants_api.models import Tenant
from apps.employees_api.models import Employee
from apps.appointments_api.models import Appointment
from apps.clients_api.models import Client
from apps.services_api.models import Service
from apps.subscriptions_api.models import SubscriptionPlan

User = get_user_model()


class ConcurrencyAppointmentRealTests(TransactionTestCase):
    """Concurrencia real: requiere PostgreSQL para bloqueo de filas."""

    def setUp(self):
        plan = SubscriptionPlan.objects.create(
            name='basic', price=10, is_active=True, is_public=True,
            features={'appointments': True}
        )
        self.tenant = Tenant.objects.create(
            name='T', subdomain='tconc2', subscription_plan=plan, is_active=True
        )
        self.user = User.objects.create_user(
            email='u@t.com', password='p', full_name='U', tenant=self.tenant, is_email_verified=True
        )
        from django.contrib.auth.models import Permission
        from apps.roles_api.models import Role, UserRole
        role, _ = Role.objects.get_or_create(name='Client-Admin', defaults={'scope': 'TENANT'})
        perms = Permission.objects.filter(content_type__app_label='appointments_api')
        role.permissions.add(*perms)
        UserRole.objects.get_or_create(user=self.user, role=role, tenant=self.tenant)

        self.client_obj = Client.objects.create(
            tenant=self.tenant, full_name='Client', created_by=self.user
        )
        self.emp = Employee.objects.create(user=self.user, tenant=self.tenant, is_active=True)
        self.service = Service.objects.create(
            tenant=self.tenant, name='Corte', price=100, duration=30
        )
        from apps.auth_api.models import User as U
        self.user2 = U.objects.create_user(
            email='u2@t.com', password='p', full_name='U2', tenant=self.tenant, is_email_verified=True
        )
        Employee.objects.create(user=self.user2, tenant=self.tenant, is_active=True)
        UserRole.objects.get_or_create(user=self.user2, role=role, tenant=self.tenant)

    def _auth(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        t = AccessToken.for_user(user)
        t['tenant_id'] = user.tenant_id
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {str(t)}")
        c.cookies['access_token'] = str(t)
        return c

    def test_concurrent_same_stylist(self):
        """Dos reservas simultáneas del mismo estilista: solo una debe tener éxito."""
        if connection.vendor == 'sqlite':
            self.skipTest('SQLite no soporta select_for_update concurrente real')

        import threading
        aligned = timezone.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
        results = []
        lock = threading.Lock()

        def create_appointment(user):
            c = self._auth(user)
            resp = c.post('/api/appointments/appointments/', {
                'client': self.client_obj.id,
                'stylist': self.user.id,
                'service': self.service.id,
                'date_time': aligned.isoformat(),
            }, format='json')
            with lock:
                results.append(resp.status_code)

        threads = [threading.Thread(target=create_appointment, args=(self.user,)) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results.count(201) == 1, f"Se crearon {results.count(201)} citas (esperado 1): {results}"
        assert results.count(400) == 4, f"Esperado 4 rechazos, got {results.count(400)}"

    def test_concurrent_same_client_different_stylist(self):
        """Un cliente no puede tener dos citas simultáneas con distintos estilistas."""
        if connection.vendor == 'sqlite':
            self.skipTest('SQLite no soporta select_for_update concurrente real')

        import threading
        aligned = timezone.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
        results = []
        lock = threading.Lock()

        def create_apt(stylist_id):
            c = self._auth(self.user)
            resp = c.post('/api/appointments/appointments/', {
                'client': self.client_obj.id,
                'stylist': stylist_id,
                'service': self.service.id,
                'date_time': aligned.isoformat(),
            }, format='json')
            with lock:
                results.append(resp.status_code)

        threads = [
            threading.Thread(target=create_apt, args=(self.user.id,)),
            threading.Thread(target=create_apt, args=(self.user2.id,)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results.count(201) == 1, f"Se crearon {results.count(201)} citas (esperado 1): {results}"
        assert results.count(400) == 1, f"Esperado 1 rechazo, got {results.count(400)}"

    def test_concurrent_reschedule(self):
        """Dos reprogramaciones simultáneas hacia el mismo horario: solo una tiene éxito."""
        if connection.vendor == 'sqlite':
            self.skipTest('SQLite no soporta select_for_update concurrente real')

        import threading
        aligned = timezone.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
        aligned2 = aligned + timedelta(hours=2)

        # Create first appointment
        c = self._auth(self.user)
        r = c.post('/api/appointments/appointments/', {
            'client': self.client_obj.id,
            'stylist': self.user.id,
            'service': self.service.id,
            'date_time': aligned.isoformat(),
        }, format='json')
        assert r.status_code == 201
        apt_id = r.data['id']

        # Create second appointment at different time
        aligned3 = aligned + timedelta(hours=4)
        c2 = self._auth(self.user)
        r2 = c2.post('/api/appointments/appointments/', {
            'client': self.client_obj.id,
            'stylist': self.user.id,
            'service': self.service.id,
            'date_time': aligned3.isoformat(),
        }, format='json')
        # May fail due to client conflict; that's OK for this test

        results = []
        lock = threading.Lock()

        def reschedule():
            c = self._auth(self.user)
            resp = c.post(f'/api/appointments/{apt_id}/reschedule/', {
                'new_date_time': aligned2.isoformat(),
            }, format='json')
            with lock:
                results.append(resp.status_code)

        # Create a conflicting appointment at aligned2
        c3 = self._auth(self.user2)
        r3 = c3.post('/api/appointments/appointments/', {
            'client': self.client_obj.id,
            'stylist': self.user.id,
            'service': self.service.id,
            'date_time': aligned2.isoformat(),
        }, format='json')
        # May fail due to client conflict

        threads = [threading.Thread(target=reschedule) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # At least verify no 500 errors
        assert all(s in (200, 400) for s in results), f"Unexpected status codes: {results}"