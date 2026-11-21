"""Regresiones BE-08 / CR-16: atomicidad, lock y paywall del booking público."""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from apps.tenants_api.models import Tenant
from apps.services_api.models import Service
from apps.employees_api.models import Employee

User = get_user_model()


class BookingIntegrityTests(TestCase):
    def setUp(self):
        # `backend.settings` define `public_booking: 500/hour`, pero
        # `test_settings` omite ese scope y DRF congela THROTTLE_RATES la
        # primera vez que se importa. Se inyecta el valor real durante el test
        # para que el throttle siga activo (no se desactiva).
        rates = SimpleRateThrottle.THROTTLE_RATES
        self._original_rate = rates.get('public_booking')
        rates['public_booking'] = '500/hour'
        self.addCleanup(self._restore_rate)

        self.tenant = Tenant.objects.create(
            name='Booking', subdomain='bookingtest', is_active=True
        )
        self.user = User.objects.create_user(
            email='stylist@bookingtest.com', password='x', tenant=self.tenant,
            full_name='Estilista',
        )
        self.employee = Employee.objects.create(
            user=self.user, tenant=self.tenant, payment_type='commission',
            commission_rate=Decimal('40.00'), fixed_salary=Decimal('0.00'),
        )
        self.service = Service.objects.create(
            tenant=self.tenant, name='Corte', price=Decimal('500.00'),
            duration=30, is_active=True,
        )
        self.date = date.today() + timedelta(days=2)
        self.api = APIClient()

    def _restore_rate(self):
        rates = SimpleRateThrottle.THROTTLE_RATES
        if self._original_rate is None:
            rates.pop('public_booking', None)
        else:
            rates['public_booking'] = self._original_rate

    def _payload(self, email):
        return {
            'stylist_id': self.employee.id,
            'service_id': self.service.id,
            'date': self.date.isoformat(),
            'time': '10:00:00',
            'client_name': 'Cliente Prueba',
            'client_email': email,
        }

    def _post(self, email='cliente@bookingtest.com'):
        return self.api.post(
            f'/api/booking/{self.tenant.subdomain}/book/',
            self._payload(email), format='json',
        )

    def test_second_booking_at_same_slot_is_rejected(self):
        """Dos clientes distintos no pueden ocupar el mismo hueco del estilista."""
        first = self._post('primero@bookingtest.com')
        assert first.status_code == 201, first.data

        second = self._post('segundo@bookingtest.com')
        assert second.status_code == 409, second.data
        assert 'no está disponible' in second.data['error']

    def test_booking_locks_stylist_row_inside_atomic(self):
        """El lock del estilista debe ejecutarse dentro de transaction.atomic()."""
        observed = []
        original = User.objects.select_for_update

        def spy():
            observed.append(connection.in_atomic_block)
            return original()

        with patch.object(User.objects, 'select_for_update', side_effect=spy):
            response = self._post()

        assert response.status_code == 201, response.data
        assert observed, 'La vista no bloqueó la fila del estilista'
        assert all(observed), 'El lock se ejecutó fuera de atomic()'

    def test_past_due_tenant_cannot_accept_public_bookings(self):
        """El paywall debe aplicarse al tenant del subdomain, aunque el visitante sea anónimo."""
        Tenant.objects.filter(pk=self.tenant.pk).update(subscription_status='past_due')
        response = self._post()
        assert response.status_code == 402, response.data
        assert response.data['code'] == 'PAYMENT_REQUIRED'
