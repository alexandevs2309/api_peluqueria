"""Regresiones del foco por tenant en /api/appointments/calendar-events/."""
import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIClient

from apps.appointments_api.models import Appointment
from apps.auth_api.models import User
from apps.clients_api.models import Client
from apps.subscriptions_api.models import SubscriptionPlan
from apps.tenants_api.models import Tenant


@pytest.fixture
def calendar_scope():
    plan = SubscriptionPlan.objects.create(
        name='calendar-scope', price=10, is_active=True, is_public=True,
        features={'appointments': True},
    )
    tenant_a = Tenant.objects.create(
        name='Alpha', subdomain='calendar-alpha', subscription_plan=plan, is_active=True
    )
    tenant_b = Tenant.objects.create(
        name='Beta', subdomain='calendar-beta', subscription_plan=plan, is_active=True
    )
    superuser = User.objects.create_superuser(
        email='calendar-root@test.com', password='pass', full_name='Root'
    )
    other = User.objects.create_user(
        email='calendar-other@test.com', password='pass', full_name='Other',
        tenant=tenant_b, is_email_verified=True,
    )
    when = timezone.now() + timedelta(days=1)
    for tenant, user in ((tenant_a, superuser), (tenant_b, other)):
        client = Client.objects.create(
            tenant=tenant, full_name=f'Cliente {tenant.name}', created_by=user
        )
        Appointment.objects.create(
            tenant=tenant, client=client, stylist=user, date_time=when,
            status='scheduled', description=f'cita-{tenant.subdomain}',
        )
    start = (timezone.now() - timedelta(hours=1)).isoformat()
    end = (timezone.now() + timedelta(days=7)).isoformat()
    return tenant_a, tenant_b, superuser, other, start, end


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_superadmin_sin_filtro_ve_ambos_tenants(calendar_scope):
    _, _, superuser, _, start, end = calendar_scope
    response = _client(superuser).get(
        '/api/appointments/calendar-events/', {'start': start, 'end': end},
    )
    assert response.status_code == 200
    assert len(response.data) == 2


@pytest.mark.django_db
def test_superadmin_con_filtro_solo_ve_ese_tenant(calendar_scope):
    tenant_a, _, superuser, _, start, end = calendar_scope
    response = _client(superuser).get(
        '/api/appointments/calendar-events/',
        {'start': start, 'end': end, 'tenant': tenant_a.id},
    )
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['extendedProps']['notes'] == 'cita-calendar-alpha'


@pytest.mark.django_db
def test_tenant_inexistente_devuelve_cero(calendar_scope):
    _, _, superuser, _, start, end = calendar_scope
    for value in ('999999', 'no-es-un-id'):
        response = _client(superuser).get(
            '/api/appointments/calendar-events/',
            {'start': start, 'end': end, 'tenant': value},
        )
        assert response.status_code == 200
        assert response.data == []


@pytest.mark.django_db
def test_usuario_de_negocio_no_puede_ampliar_el_filtro(calendar_scope):
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    from apps.roles_api.models import Role, UserRole

    tenant_a, tenant_b, _, other, start, end = calendar_scope
    role, _ = Role.objects.get_or_create(name='Client-Admin', defaults={'scope': 'TENANT'})
    content_type = ContentType.objects.get(app_label='appointments_api', model='appointment')
    perm, _ = Permission.objects.get_or_create(
        codename='view_appointment', content_type=content_type,
        defaults={'name': 'view'},
    )
    role.permissions.add(perm)
    UserRole.objects.get_or_create(user=other, role=role, tenant=tenant_b)

    response = _client(other).get(
        '/api/appointments/calendar-events/',
        {'start': start, 'end': end, 'tenant': tenant_a.id},
    )
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['extendedProps']['notes'] == 'cita-calendar-beta'
