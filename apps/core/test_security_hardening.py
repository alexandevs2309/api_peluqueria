"""Regresiones de seguridad para las cinco trampas auditadas.

Las pruebas son deliberadamente negativas: verifican que el ataque o la
condición de fallo queda bloqueado, no solo que la clase o el middleware
existe.
"""
import asyncio
import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from django.core.cache import cache
from django.test import RequestFactory
from rest_framework.request import Request
from rest_framework.test import APIClient

from apps.core import tenant_permissions
from apps.core.pagination import BoundedLimitOffsetPagination
from apps.core.tenant_permissions import HasTenantPermission, TenantPermissionByAction
from apps.roles_api.role_hierarchy import get_allowed_roles, validate_role_assignment
import apps.subscriptions_api.middleware as rate_middleware_module
from apps.subscriptions_api.middleware import APIRateLimitMiddleware


def _rate_request(user_id=901, tenant_id=701, path='/api/clients/clients/'):
    tenant = SimpleNamespace(
        id=tenant_id,
        subscription_plan=SimpleNamespace(name='basic'),
    )
    request = RequestFactory().post(path)
    request.user = SimpleNamespace(
        id=user_id,
        is_authenticated=True,
        is_superuser=False,
        tenant=tenant,
    )
    request.tenant = tenant
    return request


@pytest.fixture
def tight_rate_limits(monkeypatch):
    monkeypatch.setattr(
        APIRateLimitMiddleware,
        'RATE_LIMITS',
        {'basic': {'read': 1, 'write': 2}, 'enterprise': None},
    )
    cache.clear()
    yield
    cache.clear()


def test_rate_limit_is_atomic_under_concurrency(tight_rate_limits):
    middleware = APIRateLimitMiddleware(lambda request: None)

    def call(_):
        return middleware.process_request(_rate_request()) is None

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(call, range(12)))

    assert sum(results) == 2
    assert results.count(False) == 10


def test_rate_limit_key_includes_tenant(tight_rate_limits):
    middleware = APIRateLimitMiddleware(lambda request: None)

    assert middleware.process_request(_rate_request(tenant_id=1)) is None
    assert middleware.process_request(_rate_request(tenant_id=2)) is None
    # El primer tenant ya consumió 1 de 2 escrituras; la segunda sigue permitida.
    assert middleware.process_request(_rate_request(tenant_id=1)) is None
    blocked = middleware.process_request(_rate_request(tenant_id=1))
    assert blocked is not None and blocked.status_code == 429
    # El otro tenant conserva su propio cupo.
    assert middleware.process_request(_rate_request(tenant_id=2)) is None


def test_billing_paths_consume_quota(tight_rate_limits):
    middleware = APIRateLimitMiddleware(lambda request: None)
    path = '/api/payments/payments/create_subscription_payment/'

    assert middleware.process_request(_rate_request(path=path)) is None
    assert middleware.process_request(_rate_request(path=path)) is None
    blocked = middleware.process_request(_rate_request(path=path))
    assert blocked is not None and blocked.status_code == 429


def test_real_superuser_remains_exempt(tight_rate_limits):
    request = _rate_request()
    request.user.is_superuser = True
    middleware = APIRateLimitMiddleware(lambda request: None)

    for _ in range(5):
        assert middleware.process_request(request) is None


def test_cache_outage_degrades_to_local_limiter(monkeypatch):
    class BrokenCache:
        def add(self, *args, **kwargs):
            raise RuntimeError('redis down')

        def incr(self, *args, **kwargs):
            raise RuntimeError('redis down')

        def get(self, *args, **kwargs):
            raise RuntimeError('redis down')

        def set(self, *args, **kwargs):
            raise RuntimeError('redis down')

        def delete(self, *args, **kwargs):
            return None

    monkeypatch.setattr(APIRateLimitMiddleware, 'RATE_LIMITS', {
        'basic': {'read': 1, 'write': 2}, 'enterprise': None,
    })
    monkeypatch.setattr('apps.subscriptions_api.middleware.cache', BrokenCache())
    emergency_counters = {}
    monkeypatch.setattr(
        rate_middleware_module,
        '_EMERGENCY_RATE_LIMIT_COUNTERS',
        emergency_counters,
    )
    middleware = APIRateLimitMiddleware(lambda request: None)

    assert middleware.process_request(_rate_request()) is None
    assert middleware.process_request(_rate_request()) is None
    blocked_request = _rate_request()
    blocked = middleware.process_request(blocked_request)
    response = middleware.process_response(blocked_request, blocked)
    assert blocked.status_code == 429
    assert response['X-RateLimit-Degraded'] == '1'
    assert emergency_counters and max(count for count, _ in emergency_counters.values()) == 3


def test_object_permission_denies_tenantless_object(monkeypatch):
    monkeypatch.setattr(tenant_permissions, '_check_permission_in_db', lambda *args: True)
    tenant = SimpleNamespace(id=1)
    request = SimpleNamespace(
        user=SimpleNamespace(id=9, is_authenticated=True, is_superuser=False, tenant=tenant),
        tenant=tenant,
        method='GET',
    )
    view = SimpleNamespace(action='retrieve', permission_map={'retrieve': 'app.view_model'})

    assert TenantPermissionByAction().has_object_permission(
        request, view, SimpleNamespace()
    ) is False

    view.allow_tenantless_objects = True
    assert TenantPermissionByAction().has_object_permission(
        request, view, SimpleNamespace()
    ) is True


def test_object_permission_resolves_nested_tenant_and_rejects_cross_tenant(monkeypatch):
    monkeypatch.setattr(tenant_permissions, '_check_permission_in_db', lambda *args: True)
    tenant = SimpleNamespace(id=1)
    other_tenant = SimpleNamespace(id=2)
    request = SimpleNamespace(
        user=SimpleNamespace(id=9, is_authenticated=True, is_superuser=False, tenant=tenant),
        tenant=tenant,
        method='PUT',
    )
    view = SimpleNamespace(action='update', permission_map={'update': 'app.change_model'})

    own = SimpleNamespace(employee=SimpleNamespace(tenant=tenant))
    foreign = SimpleNamespace(employee=SimpleNamespace(tenant=other_tenant))

    assert TenantPermissionByAction().has_object_permission(request, view, own) is True
    assert TenantPermissionByAction().has_object_permission(request, view, foreign) is False


def test_has_tenant_permission_also_denies_unknown_object(monkeypatch):
    monkeypatch.setattr(tenant_permissions, '_check_permission_in_db', lambda *args: True)
    tenant = SimpleNamespace(id=1)
    request = SimpleNamespace(
        user=SimpleNamespace(id=9, is_authenticated=True, is_superuser=False, tenant=tenant),
        tenant=tenant,
        method='GET',
    )
    permission = type('P', (HasTenantPermission,), {
        'required_permission': 'app.view_model',
    })()

    assert permission.has_object_permission(request, SimpleNamespace(), SimpleNamespace()) is False


def test_pagination_has_hard_limit():
    paginator = BoundedLimitOffsetPagination()
    request = Request(RequestFactory().get('/?limit=1000000'))

    assert paginator.max_limit == 200
    assert paginator.get_limit(request) == 200


def test_legacy_role_cannot_delegate_superadmin():
    allowed, message = validate_role_assignment('SuperAdmin', 'SuperAdmin', False)

    assert allowed is False
    assert message
    assert 'SuperAdmin' not in get_allowed_roles('SuperAdmin', False)


@pytest.mark.django_db
def test_whatsapp_webhook_fails_closed_without_secret():
    from apps.settings_api.barbershop_models import BarbershopSettings
    from apps.settings_api.barbershop_views import BarbershopSettingsViewSet
    from apps.tenants_api.models import Tenant

    tenant = Tenant.objects.create(name='Webhook sin secreto', subdomain='ws-no-secret')
    settings = BarbershopSettings.objects.create(
        tenant=tenant,
        whatsapp_instance_name='ws_no_secret',
        whatsapp_webhook_secret='',
    )
    body = json.dumps({
        'event': 'connection.update',
        'instance': 'ws_no_secret',
        'data': {'state': 'open'},
    })
    request = RequestFactory().post(
        '/api/settings/barbershop/whatsapp_webhook/',
        data=body,
        content_type='application/json',
    )
    view = BarbershopSettingsViewSet.as_view({'post': 'whatsapp_webhook'})

    response = view(request)

    assert response.status_code == 401
    settings.refresh_from_db()
    assert settings.whatsapp_status != 'connected'


@pytest.mark.django_db
def test_whatsapp_webhook_rejects_wrong_token_and_accepts_right_token():
    from apps.settings_api.barbershop_models import BarbershopSettings
    from apps.settings_api.barbershop_views import BarbershopSettingsViewSet
    from apps.tenants_api.models import Tenant

    tenant = Tenant.objects.create(name='Webhook con secreto', subdomain='ws-con-secret')
    secret = 'token-de-prueba'
    settings = BarbershopSettings.objects.create(
        tenant=tenant,
        whatsapp_instance_name='ws_con_secret',
        whatsapp_webhook_secret=secret,
    )
    body = json.dumps({
        'event': 'connection.update',
        'instance': 'ws_con_secret',
        'data': {'state': 'open', 'phone': '8095550000'},
    })
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    view = BarbershopSettingsViewSet.as_view({'post': 'whatsapp_webhook'})
    url = '/api/settings/barbershop/whatsapp_webhook/'

    bad = RequestFactory().post(
        url + '?token=incorrecto', data=body, content_type='application/json'
    )
    assert view(bad).status_code == 401

    good = RequestFactory().post(
        url + f'?token={secret}',
        data=body,
        content_type='application/json',
        HTTP_X_WEBHOOK_SIGNATURE=signature,
    )
    assert view(good).status_code == 200
    settings.refresh_from_db()
    assert settings.whatsapp_status == 'connected'


def test_paypal_cached_completion_is_not_shared_across_owners():
    from django.core.cache import cache
    from apps.subscriptions_api.views import (
        _cached_completion_belongs_to,
        _cache_completion,
    )

    cache.clear()
    key = 'security-hardening-capture'
    request = SimpleNamespace(user=SimpleNamespace(id=11))
    tenant = SimpleNamespace(id=22)
    _cache_completion(key, {'message': 'ok'}, request, tenant)

    assert _cached_completion_belongs_to(request, tenant, key) is True
    other = SimpleNamespace(user=SimpleNamespace(id=33))
    assert _cached_completion_belongs_to(other, tenant, key) is False
    assert cache.get(key) is None
    cache.clear()


@pytest.mark.django_db
def test_bulk_tenant_actions_validate_ids_and_audit():
    from apps.audit_api.models import AuditLog
    from apps.auth_api.factories import UserFactory
    from apps.tenants_api.models import Tenant

    admin = UserFactory(is_superuser=True)
    client = APIClient()
    client.force_authenticate(user=admin)
    tenant = Tenant.objects.create(name='Bulk auditado', subdomain='bulk-auditado')
    url = '/api/tenants/bulk_activate/'

    invalid = client.post(url, {'tenant_ids': [str(tenant.id)]}, format='json')
    assert invalid.status_code == 400

    valid = client.post(url, {'tenant_ids': [tenant.id]}, format='json')
    assert valid.status_code == 200
    assert AuditLog.objects.filter(action='BULK_ACTIVATE', object_id=tenant.id).exists()


@pytest.mark.django_db
def test_non_superuser_cannot_deactivate_global_plan():
    from apps.auth_api.factories import UserFactory
    from apps.subscriptions_api.models import SubscriptionPlan

    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    plan = SubscriptionPlan.objects.create(
        name='pro', price='1.00', is_active=True
    )

    response = client.post(f'/api/subscriptions/plans/{plan.id}/deactivate/')

    assert response.status_code == 403
    plan.refresh_from_db()
    assert plan.is_active is True


def test_no_show_job_stops_at_bounded_batches(monkeypatch):
    from apps.notifications_api import tasks

    batch_filters = []

    class BatchQuerySet:
        def select_related(self, *args):
            return self

        def order_by(self, *args):
            return self

        def __getitem__(self, item):
            if len(batch_filters) > 2:
                return []
            appointment_id = 100 + len(batch_filters)
            return [SimpleNamespace(
                id=appointment_id,
                client=None,
                client_id=None,
                stylist_id=None,
                date_time=None,
                tenant_id=None,
            )]

    class UpdateQuerySet:
        def __init__(self, ids):
            self.ids = ids

        def update(self, **kwargs):
            return len(self.ids)

    class FakeManager:
        def filter(self, **kwargs):
            if 'id__gt' in kwargs:
                batch_filters.append(kwargs)
                return BatchQuerySet()
            if 'id__in' in kwargs:
                return UpdateQuerySet(kwargs['id__in'])
            raise AssertionError(f'Filtro inesperado: {kwargs}')

    from apps.appointments_api import models as appointment_models

    monkeypatch.setattr(
        appointment_models, 'Appointment', SimpleNamespace(objects=FakeManager())
    )
    monkeypatch.setattr(tasks, 'NO_SHOW_BATCH_SIZE', 1)
    monkeypatch.setattr(tasks, 'MAX_NO_SHOW_BATCHES', 2)

    result = tasks.mark_expired_appointments()

    assert '2' in result
    assert len(batch_filters) == 2  # el tope de lotes se respeta sin consultar más


def test_sse_stream_has_absolute_lifetime(monkeypatch):
    import apps.notifications_api.sse as sse

    class FakePubSub:
        async def subscribe(self, channel):
            return None

        async def get_message(self, **kwargs):
            return {'type': 'message', 'data': json.dumps({'type': 'ping'})}

        async def unsubscribe(self, channel):
            return None

        async def close(self):
            return None

    class FakeRedis:
        def pubsub(self):
            return FakePubSub()

        async def close(self):
            return None

    async def no_notifications(user):
        return []

    monkeypatch.setattr(sse.aioredis, 'from_url', lambda *args, **kwargs: FakeRedis())
    monkeypatch.setattr(sse, '_get_unread_notifications', no_notifications)
    monkeypatch.setenv('RUNNING_SSE', 'true')

    clock = iter([1000, 1000 + sse.SSE_MAX_LIFETIME_SECONDS, 9999])
    monkeypatch.setattr(sse, '_stream_clock', lambda: next(clock))

    request = RequestFactory().get('/api/notifications/stream/')
    request.user = SimpleNamespace(id=4242, is_authenticated=True)

    async def consume(response):
        return [chunk async for chunk in response.streaming_content]

    response = asyncio.run(sse.notification_sse(request))
    chunks = asyncio.run(consume(response))

    assert response.status_code == 200
    assert len(chunks) == 1  # solo el evento init; se corta antes del primer heartbeat
    first_chunk = chunks[0].decode() if isinstance(chunks[0], bytes) else chunks[0]
    assert first_chunk.startswith('event: init')
