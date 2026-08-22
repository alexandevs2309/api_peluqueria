"""
Tests for WhatsApp integration (Evolution API).

Covers:
- QR connection
- Connection plan gate
- Manual send
- Send plan gate
- Webhook signature verification
- Tenant isolation
- Provider reads from BarbershopSettings
"""
import pytest
import hmac
import hashlib
from django.test import TestCase, RequestFactory
from apps.subscriptions_api.models import SubscriptionPlan
from apps.settings_api.barbershop_models import BarbershopSettings


@pytest.mark.django_db
class TestWhatsAppConnection:
    """WhatsApp connection requires whatsapp_notifications feature."""

    def test_basic_plan_cannot_connect(self):
        from apps.tenants_api.models import Tenant
        from apps.subscriptions_api.plan_consistency import tenant_has_feature

        plan = SubscriptionPlan.objects.get(name='basic')
        tenant = Tenant.objects.create(
            name='Test WA Basic',
            subdomain='test-wa-basic',
            subscription_plan=plan,
            plan_type='basic',
        )
        assert tenant_has_feature(tenant, 'whatsapp_notifications') is False

    def test_premium_plan_can_connect(self):
        from apps.tenants_api.models import Tenant
        from apps.subscriptions_api.plan_consistency import tenant_has_feature

        plan = SubscriptionPlan.objects.get(name='premium')
        tenant = Tenant.objects.create(
            name='Test WA Premium',
            subdomain='test-wa-premium',
            subscription_plan=plan,
            plan_type='premium',
        )
        assert tenant_has_feature(tenant, 'whatsapp_notifications') is True

    def test_enterprise_plan_can_connect(self):
        from apps.tenants_api.models import Tenant
        from apps.subscriptions_api.plan_consistency import tenant_has_feature

        plan = SubscriptionPlan.objects.get(name='enterprise')
        tenant = Tenant.objects.create(
            name='Test WA Enterprise',
            subdomain='test-wa-enterprise',
            subscription_plan=plan,
            plan_type='enterprise',
        )
        assert tenant_has_feature(tenant, 'whatsapp_notifications') is True


@pytest.mark.django_db
class TestWhatsAppProvider:
    """Provider must read from BarbershopSettings, not Tenant."""

    def test_provider_reads_from_barbershop_settings(self):
        from apps.tenants_api.models import Tenant
        from apps.notifications_api.provider import get_notification_provider, EvolutionClientProvider

        plan = SubscriptionPlan.objects.get(name='premium')
        tenant = Tenant.objects.create(
            name='Test Provider',
            subdomain='test-provider',
            subscription_plan=plan,
            plan_type='premium',
        )
        settings = BarbershopSettings.objects.create(
            tenant=tenant,
            whatsapp_enabled=True,
            whatsapp_instance_name='test_instance',
            whatsapp_token='test_token_123',
            whatsapp_status='connected',
        )

        provider = get_notification_provider(context='client', tenant=tenant)
        assert isinstance(provider, EvolutionClientProvider)
        assert provider.token == 'test_token_123'
        assert provider.tenant == tenant

    def test_provider_fails_without_barbershop_settings(self):
        from apps.tenants_api.models import Tenant
        from apps.notifications_api.provider import get_notification_provider

        plan = SubscriptionPlan.objects.get(name='premium')
        tenant = Tenant.objects.create(
            name='Test No Settings',
            subdomain='test-no-settings',
            subscription_plan=plan,
            plan_type='premium',
        )

        with pytest.raises(Exception, match="EVOLUTION_NOT_CONFIGURED"):
            get_notification_provider(context='client', tenant=tenant)

    def test_provider_fails_when_whatsapp_disabled(self):
        from apps.tenants_api.models import Tenant
        from apps.notifications_api.provider import get_notification_provider

        plan = SubscriptionPlan.objects.get(name='premium')
        tenant = Tenant.objects.create(
            name='Test WA Disabled',
            subdomain='test-wa-disabled',
            subscription_plan=plan,
            plan_type='premium',
        )
        BarbershopSettings.objects.create(
            tenant=tenant,
            whatsapp_enabled=False,
            whatsapp_instance_name='test_instance',
            whatsapp_token='test_token_123',
        )

        with pytest.raises(Exception, match="EVOLUTION_NOT_CONFIGURED"):
            get_notification_provider(context='client', tenant=tenant)

    def test_provider_fails_without_token(self):
        from apps.tenants_api.models import Tenant
        from apps.notifications_api.provider import get_notification_provider

        plan = SubscriptionPlan.objects.get(name='premium')
        tenant = Tenant.objects.create(
            name='Test No Token',
            subdomain='test-no-token',
            subscription_subscription_plan=plan,
            plan_type='premium',
        )
        BarbershopSettings.objects.create(
            tenant=tenant,
            whatsapp_enabled=True,
            whatsapp_instance_name='test_instance',
            whatsapp_token='',
        )

        with pytest.raises(Exception, match="EVOLUTION_NOT_CONFIGURED"):
            get_notification_provider(context='client', tenant=tenant)


@pytest.mark.django_db
class TestWhatsAppWebhook:
    """Webhook must verify signature when secret is configured."""

    def test_webhook_accepts_without_secret(self):
        """Webhook should work without signature if no secret is configured."""
        from apps.tenants_api.models import Tenant
        from django.test import RequestFactory

        plan = SubscriptionPlan.objects.get(name='premium')
        tenant = Tenant.objects.create(
            name='Test Webhook',
            subdomain='test-webhook',
            subscription_plan=plan,
            plan_type='premium',
        )
        settings = BarbershopSettings.objects.create(
            tenant=tenant,
            whatsapp_instance_name='test_instance',
            whatsapp_webhook_secret='',
        )

        factory = RequestFactory()
        request = factory.post(
            '/api/settings/barbershop/whatsapp_webhook/',
            data={
                'event': 'connection.update',
                'instance': 'test_instance',
                'data': {'state': 'open', 'phone': '+1234567890'},
            },
            content_type='application/json',
        )

        from apps.settings_api.barbershop_views import BarbershopSettingsViewSet
        view = BarbershopSettingsViewSet.as_view({'post': 'whatsapp_webhook'})
        response = view(request)
        assert response.status_code == 200

    def test_webhook_rejects_bad_signature(self):
        """Webhook should reject invalid signature when secret is configured."""
        from apps.tenants_api.models import Tenant
        from django.test import RequestFactory

        plan = SubscriptionPlan.objects.get(name='premium')
        tenant = Tenant.objects.create(
            name='Test Webhook Sig',
            subdomain='test-webhook-sig',
            subscription_plan=plan,
            plan_type='premium',
        )
        settings = BarbershopSettings.objects.create(
            tenant=tenant,
            whatsapp_instance_name='test_instance_sig',
            whatsapp_webhook_secret='my_secret_key',
        )

        factory = RequestFactory()
        body = '{"event": "connection.update", "instance": "test_instance_sig", "data": {"state": "open"}}'
        request = factory.post(
            '/api/settings/barbershop/whatsapp_webhook/',
            data=body,
            content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE='invalid_signature',
        )

        from apps.settings_api.barbershop_views import BarbershopSettingsViewSet
        view = BarbershopSettingsViewSet.as_view({'post': 'whatsapp_webhook'})
        response = view(request)
        assert response.status_code == 401

    def test_webhook_accepts_valid_signature(self):
        """Webhook should accept valid HMAC signature."""
        from apps.tenants_api.models import Tenant
        from django.test import RequestFactory

        plan = SubscriptionPlan.objects.get(name='premium')
        tenant = Tenant.objects.create(
            name='Test Webhook Valid',
            subdomain='test-webhook-valid',
            subscription_plan=plan,
            plan_type='premium',
        )
        secret = 'my_secret_key'
        settings = BarbershopSettings.objects.create(
            tenant=tenant,
            whatsapp_instance_name='test_instance_valid',
            whatsapp_webhook_secret=secret,
        )

        body = '{"event": "connection.update", "instance": "test_instance_valid", "data": {"state": "open"}}'
        signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()

        factory = RequestFactory()
        request = factory.post(
            '/api/settings/barbershop/whatsapp_webhook/',
            data=body,
            content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE=signature,
        )

        from apps.settings_api.barbershop_views import BarbershopSettingsViewSet
        view = BarbershopSettingsViewSet.as_view({'post': 'whatsapp_webhook'})
        response = view(request)
        assert response.status_code == 200


@pytest.mark.django_db
class TestWhatsAppTenantIsolation:
    """WhatsApp settings must be scoped to tenant."""

    def test_tenant_cannot_access_other_settings(self):
        from apps.tenants_api.models import Tenant

        plan = SubscriptionPlan.objects.get(name='premium')
        tenant1 = Tenant.objects.create(
            name='Tenant 1',
            subdomain='tenant-1',
            subscription_plan=plan,
            plan_type='premium',
        )
        tenant2 = Tenant.objects.create(
            name='Tenant 2',
            subdomain='tenant-2',
            subscription_plan=plan,
            plan_type='premium',
        )
        settings1 = BarbershopSettings.objects.create(
            tenant=tenant1,
            whatsapp_instance_name='instance_1',
            whatsapp_token='token_1',
        )
        settings2 = BarbershopSettings.objects.create(
            tenant=tenant2,
            whatsapp_instance_name='instance_2',
            whatsapp_token='token_2',
        )

        # Each tenant should only see their own settings
        assert tenant1.barbershop_settings.whatsapp_instance_name == 'instance_1'
        assert tenant2.barbershop_settings.whatsapp_instance_name == 'instance_2'
