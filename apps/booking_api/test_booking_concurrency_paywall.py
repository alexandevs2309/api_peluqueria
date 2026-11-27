"""Regresiones BE-08 / CR-16: atomicidad, lock y paywall del booking público."""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from apps.tenants_api.models import Tenant
from apps.tenants_api.serializers import TenantSerializer
from apps.services_api.models import Service, ServiceEmployee
from apps.employees_api.models import Employee
from apps.appointments_api.models import Appointment

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

    def test_each_booking_keeps_the_name_entered_by_the_visitor(self):
        """Un mismo teléfono reutiliza el Client, pero cada cita debe mostrar su nombre."""
        first_payload = self._payload('')
        first_payload.pop('client_email')
        first_payload['client_phone'] = '8095551234'
        first_payload['client_name'] = 'Yeiko'
        first = self.api.post(
            f'/api/booking/{self.tenant.subdomain}/book/', first_payload, format='json'
        )
        assert first.status_code == 201, first.data

        second_payload = dict(first_payload)
        second_payload['date'] = (self.date + timedelta(days=1)).isoformat()
        second_payload['client_name'] = 'Alexander'
        second = self.api.post(
            f'/api/booking/{self.tenant.subdomain}/book/', second_payload, format='json'
        )

        assert second.status_code == 201, second.data
        assert second.data['client_name'] == 'Alexander'
        appointment = Appointment.objects.get(id=second.data['id'])
        assert appointment.client_name == 'Alexander'
        assert appointment.client.full_name == 'Yeiko'  # el contacto se reutiliza

    def test_past_due_tenant_cannot_accept_public_bookings(self):
        """El paywall debe aplicarse al tenant del subdomain, aunque el visitante sea anónimo."""
        Tenant.objects.filter(pk=self.tenant.pk).update(subscription_status='past_due')
        response = self._post()
        assert response.status_code == 402, response.data
        assert response.data['code'] == 'PAYMENT_REQUIRED'

    def test_stylists_can_be_filtered_by_service(self):
        """El portal filtra profesionales por servicio sin consultar una relation inexistente."""
        ServiceEmployee.objects.create(service=self.service, employee=self.employee)

        response = self.api.get(
            f'/api/booking/{self.tenant.subdomain}/stylists/',
            {'service_id': self.service.id},
        )

        assert response.status_code == 200, response.data
        assert [item['id'] for item in response.data] == [self.employee.id]

    def test_public_info_never_exposes_business_email(self):
        """El correo del negocio es su identidad de acceso: no debe filtrarse al visitante."""
        Tenant.objects.filter(pk=self.tenant.pk).update(
            contact_email='aventuracuevas@icloud.com',
            contact_phone='8095550000',
        )

        response = self.api.get(f'/api/booking/{self.tenant.subdomain}/info/')

        assert response.status_code == 200, response.data
        assert 'contact_email' not in response.data
        assert response.data['contact_phone'] == '8095550000'

    @override_settings(FRONTEND_URL='https://app.auronsuite.com/')
    def test_booking_url_is_derived_from_tenant_subdomain(self):
        """El enlace público es propiedad del negocio, nunca del visitante."""
        expected = 'https://app.auronsuite.com/reservar/bookingtest'

        response = self.api.get(f'/api/booking/{self.tenant.subdomain}/info/')
        assert response.status_code == 200, response.data
        assert response.data['booking_url'] == expected

        assert TenantSerializer(self.tenant).data['booking_url'] == expected

    @override_settings(FRONTEND_URL='')
    def test_booking_url_without_frontend_origin_is_relative(self):
        response = self.api.get(f'/api/booking/{self.tenant.subdomain}/info/')
        assert response.data['booking_url'] == '/reservar/bookingtest'
