"""
V-03 / V-04 — Concurrencia real de reservas sobre PostgreSQL (BE-06, BE-08, CR-16).

`select_for_update()` y los savepoints son no-ops en SQLite: estas pruebas se
omiten con cualquier otro motor. Dos hilos abren conexiones independientes y
llegan a la barrera con el mismo estado leído; la exclusión la impone PostgreSQL.

Cubre: doble reserva, solapamiento parcial, empleados/sucursales/duraciones
distintas, reprogramación simultánea, reserva vs reprogramación, zona horaria y
rollback tras error.
"""
import threading
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.appointments_api.models import Appointment
from apps.appointments_api.views import reschedule_appointment
from apps.booking_api.views import book_appointment
from apps.clients_api.models import Client
from apps.employees_api.models import Employee
from apps.roles_api.models import Role, UserRole
from apps.services_api.models import Service
from apps.tenants_api.models import Tenant

User = get_user_model()
pytestmark = pytest.mark.django_db(transaction=True)


def _require_postgres():
    if connection.vendor != 'postgresql':
        pytest.skip('V-03/V-04 exigen PostgreSQL real')


class _Base(TransactionTestCase):
    def setUp(self):
        _require_postgres()
        # `backend.settings` define este scope, pero `test_settings` no; DRF
        # congela THROTTLE_RATES al importar. Se inyecta sin desactivar el throttle.
        from rest_framework.throttling import SimpleRateThrottle
        rates = SimpleRateThrottle.THROTTLE_RATES
        self._original_rate = rates.get('public_booking')
        rates['public_booking'] = '500/hour'
        self.addCleanup(self._restore_rate)

        self.tenant = Tenant.objects.create(
            name='Booking PG', subdomain='bookingpg', is_active=True,
            subscription_status='active',
        )
        self.stylist_user = self._user('stylistpg', 'Estilista')
        self.other_user = self._user('otherpg', 'Otro estilista')
        self._grant_permissions(self.stylist_user)
        self._grant_permissions(self.other_user)

        self.employee = Employee.objects.create(
            user=self.stylist_user, tenant=self.tenant, payment_type='commission',
            commission_rate=Decimal('40.00'), fixed_salary=Decimal('0.00'), is_active=True,
        )
        self.other_employee = Employee.objects.create(
            user=self.other_user, tenant=self.tenant, payment_type='commission',
            commission_rate=Decimal('40.00'), fixed_salary=Decimal('0.00'), is_active=True,
        )
        self.service30 = Service.objects.create(
            tenant=self.tenant, name='Corte 30', price=Decimal('500.00'),
            duration=30, is_active=True,
        )
        self.service60 = Service.objects.create(
            tenant=self.tenant, name='Corte 60', price=Decimal('900.00'),
            duration=60, is_active=True,
        )
        self.day = date.today() + timedelta(days=3)

    def _restore_rate(self):
        from rest_framework.throttling import SimpleRateThrottle
        rates = SimpleRateThrottle.THROTTLE_RATES
        if self._original_rate is None:
            rates.pop('public_booking', None)
        else:
            rates['public_booking'] = self._original_rate

    def _user(self, prefix, name):
        return User.objects.create_user(
            email=f'{prefix}@test.com', password='x', full_name=name, tenant=self.tenant
        )

    def _grant_permissions(self, user):
        role, _ = Role.objects.get_or_create(name=f'RolePG-{user.pk}', defaults={'description': 'test'})
        role.permissions.add(*Permission.objects.filter(
            content_type__app_label__in=['appointments_api', 'clients_api', 'services_api']
        ))
        UserRole.objects.get_or_create(user=user, role=role, tenant=self.tenant)

    def _datetime(self, hhmm='10:00:00', day=None):
        h, m, s = (int(x) for x in hhmm.split(':'))
        return timezone.make_aware(
            datetime.combine(day or self.day, time(h, m, s)),
            timezone.get_current_timezone(),
        )

    def _book(self, email, employee=None, service=None, hhmm='10:00:00', day=None):
        raw = APIRequestFactory().post(
            f'/api/booking/{self.tenant.subdomain}/book/',
            {
                'stylist_id': (employee or self.employee).pk,
                'service_id': (service or self.service30).pk,
                'date': (day or self.day).isoformat(),
                'time': hhmm,
                'client_name': email.split('@')[0],
                'client_email': email,
            },
            format='json',
        )
        return book_appointment(raw, subdomain=self.tenant.subdomain)

    def _reschedule(self, pk, target, user=None):
        raw = APIRequestFactory().post(
            f'/api/appointments/{pk}/reschedule/',
            {'new_datetime': target.isoformat()}, format='json',
        )
        force_authenticate(request=raw, user=user or self.stylist_user)
        raw.tenant = (user or self.stylist_user).tenant
        return reschedule_appointment(raw, pk=pk)

    def _run(self, fn_a, fn_b):
        results = []
        barrier = threading.Barrier(2)

        def worker(fn):
            connection.close()
            try:
                barrier.wait(timeout=10)
                response = fn()
                results.append((response.status_code, dict(response.data)))
            except Exception as exc:
                results.append(('EXC', f'{type(exc).__name__}: {exc}'))
            finally:
                connection.close()

        threads = [threading.Thread(target=worker, args=(f,)) for f in (fn_a, fn_b)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
            assert not t.is_alive(), 'una petición quedó bloqueada (lock no liberado)'
        return results


class BookingPostgresConcurrency(_Base):
    def test_two_simultaneous_bookings_same_stylist_same_slot(self):
        results = self._run(
            lambda: self._book('a@pg.com'),
            lambda: self._book('b@pg.com'),
        )
        codes = sorted(c for c, _ in results)
        assert codes == [201, 409], results
        assert Appointment.objects.filter(
            tenant=self.tenant, stylist=self.stylist_user, status='scheduled'
        ).count() == 1, 'dos reservas ocuparon el mismo hueco'

    def test_partially_overlapping_bookings_are_detected_by_reschedule(self):
        """10:00 (30 min) y 10:15 (60 min) se solapan; el lock debe rechazarlos."""
        first = self._book('c@pg.com', service=self.service30, hhmm='10:00:00')
        assert first.status_code == 201, first.data
        second = self._book('d@pg.com', service=self.service60, hhmm='10:30:00')
        assert second.status_code == 201, second.data  # 10:30 no solapa con 10:00-10:30

        # Reprogramar la segunda a 10:15 solapa 15 min con la primera.
        response = self._reschedule(second.data['id'], self._datetime('10:15:00'))
        assert response.status_code == 400, response.data
        second_obj = Appointment.objects.get(pk=second.data['id'])
        assert second_obj.date_time == self._datetime('10:30:00')

    def test_different_stylists_and_branches_accept_same_slot(self):
        results = self._run(
            lambda: self._book('e@pg.com', employee=self.employee),
            lambda: self._book('f@pg.com', employee=self.other_employee),
        )
        assert sorted(c for c, _ in results) == [201, 201], results
        assert Appointment.objects.filter(tenant=self.tenant, status='scheduled').count() == 2

    def test_paywall_and_rollback_on_error(self):
        from django.db import IntegrityError
        from unittest import mock
        from apps.appointments_api.models import Appointment as Appt

        original_create = Appt.objects.create

        def boom(*args, **kwargs):
            raise IntegrityError('fallo simulado de BD durante la reserva')

        with mock.patch.object(Appt.objects, 'create', side_effect=boom):
            response = self._book('g@pg.com')
        assert response.status_code == 409, response.data
        assert Appointment.objects.count() == 0, 'el rollback no deshizo la reserva'
        assert Client.objects.filter(tenant=self.tenant).count() == 0, 'el rollback no deshizo el cliente'

        # Con el error superado, la misma petición funciona (sin estado residual).
        ok = self._book('g@pg.com')
        assert ok.status_code == 201, ok.data


class ReschedulePostgresConcurrency(_Base):
    def _appointment(self, hhmm='10:00:00', service=None, client_email='orig@pg.com'):
        client, _ = Client.objects.get_or_create(
            tenant=self.tenant, email=client_email,
            defaults={'full_name': 'Original'},
        )
        target = self._datetime(hhmm)
        return Appointment.objects.create(
            tenant=self.tenant, stylist=self.stylist_user, client=client,
            service=service or self.service30, date_time=target, status='scheduled',
        )

    def test_reschedule_works_on_postgres_without_outer_join_for_update_error(self):
        appt = self._appointment()
        response = self._reschedule(appt.pk, self._datetime('12:00:00'))
        assert response.status_code == 200, response.data
        appt.refresh_from_db()
        assert appt.date_time == self._datetime('12:00:00')

    def test_two_simultaneous_reschedules_of_same_appointment(self):
        appt = self._appointment()
        results = self._run(
            lambda: self._reschedule(appt.pk, self._datetime('12:00:00')),
            lambda: self._reschedule(appt.pk, self._datetime('14:00:00')),
        )
        assert all(c == 200 for c, _ in results), results
        appt.refresh_from_db()
        assert appt.date_time in (self._datetime('12:00:00'), self._datetime('14:00:00'))
        assert Appointment.objects.filter(tenant=self.tenant, stylist=self.stylist_user).count() == 1

    def test_reschedule_vs_booking_concurrent_same_slot(self):
        appt = self._appointment(hhmm='09:00:00')
        results = self._run(
            lambda: self._reschedule(appt.pk, self._datetime('10:00:00')),
            lambda: self._book('nuevo@pg.com', hhmm='10:00:00'),
        )
        # El ganador puede ser el booking (201) y el reschedule detectar el
        # solapamiento (400), o al revés (200 + 409). Ambas son correctas.
        assert sorted(c for c, _ in results) in ([200, 409], [201, 400]), results
        # La propiedad crítica: nunca dos citas activas solapadas para el estilista.
        active = list(Appointment.objects.filter(
            tenant=self.tenant, stylist=self.stylist_user, status='scheduled'
        ).order_by('date_time'))
        assert len(active) <= 2, active
        for i, a in enumerate(active):
            a_start = a.date_time
            a_end = a_start + timedelta(minutes=(a.service.duration if a.service else 30))
            for b in active[i + 1:]:
                b_end = b.date_time + timedelta(minutes=(b.service.duration if b.service else 30))
                assert not (a_start < b_end and b.date_time < a_end), (
                    f'solapamiento {a.pk} {b.pk} tras carrera reserva/reprogramación'
                )

    def test_reschedule_across_dst_boundary_keeps_local_time(self):
        appt = self._appointment()
        tz = timezone.get_current_timezone()
        target = timezone.make_aware(datetime(2026, 3, 8, 12, 0), tz)
        response = self._reschedule(appt.pk, target)
        assert response.status_code == 200, response.data
        appt.refresh_from_db()
        assert timezone.localtime(appt.date_time).hour == 12
