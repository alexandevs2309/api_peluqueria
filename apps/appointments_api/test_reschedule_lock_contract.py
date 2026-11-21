"""Regresiones BE-06 / CR-16 / CR-01 para `reschedule_appointment`."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.tenants_api.models import Tenant
from apps.services_api.models import Service
from apps.clients_api.models import Client
from apps.appointments_api.models import Appointment

User = get_user_model()


@pytest.mark.django_db
class RescheduleLockTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='Reschedule', subdomain='reschedulelock', is_active=True
        )
        self.user = User.objects.create_user(
            email='resched@test.com', password='x', tenant=self.tenant
        )
        self.client_obj = Client.objects.create(
            tenant=self.tenant, full_name='Cliente', email='cliente@resched.com'
        )
        self.service = Service.objects.create(
            tenant=self.tenant, name='Corte', price='500.00', duration=30
        )
        now = timezone.now().replace(microsecond=0)
        self.appointment = Appointment.objects.create(
            tenant=self.tenant, client=self.client_obj, stylist=self.user,
            service=self.service, date_time=now + timedelta(hours=1), status='scheduled',
        )
        self.target = (now + timedelta(hours=3)).isoformat()
        from django.contrib.auth.models import Permission
        from apps.roles_api.models import Role, UserRole
        from rest_framework_simplejwt.tokens import AccessToken

        role, _ = Role.objects.get_or_create(name='RescheduleRole', defaults={'description': 'Test'})
        role.permissions.add(*Permission.objects.filter(
            content_type__app_label__in=['appointments_api', 'clients_api', 'services_api']
        ))
        UserRole.objects.get_or_create(user=self.user, role=role, tenant=self.tenant)

        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        token = AccessToken.for_user(self.user)
        token['tenant_id'] = self.tenant.id
        self.api.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token)}')

    def test_locked_appointment_querysets_have_no_select_related(self):
        """PostgreSQL rechaza FOR UPDATE sobre el lado nullable de un outer join."""
        from django.db.models.query import QuerySet

        original = QuerySet.select_related
        observed = []

        def spy(queryset, *args, **kwargs):
            observed.append((args, queryset.query.select_for_update))
            return original(queryset, *args, **kwargs)

        with patch.object(QuerySet, 'select_related', spy):
            response = self.api.post(
                f'/api/appointments/{self.appointment.pk}/reschedule/',
                {'new_datetime': self.target}, format='json',
            )

        assert response.status_code == 200, response.data
        assert not any(args and args[0] == 'service' and locked for args, locked in observed), (
            'select_for_update() no debe combinarse con select_related("service")'
        )

    def test_backend_contract_uses_new_datetime(self):
        """El contrato vigente es `new_datetime`; el alias legacy debe rechazarse."""
        ok = self.api.post(
            f'/api/appointments/{self.appointment.pk}/reschedule/',
            {'new_datetime': self.target}, format='json',
        )
        assert ok.status_code == 200, ok.data

        legacy = self.api.post(
            f'/api/appointments/{self.appointment.pk}/reschedule/',
            {'new_date_time': self.target}, format='json',
        )
        assert legacy.status_code == 400
