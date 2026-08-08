import pytest
import os
import sys
from django.conf import settings
from django.urls import resolve, Resolver404, clear_url_caches
from django.test import Client
from apps.auth_api.models import User
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan

@pytest.mark.django_db
class TestSecurityRegressions:

    def setup_method(self):
        clear_url_caches()

    def teardown_method(self):
        clear_url_caches()

    def test_cron_api_key_fail_closed(self):
        """
        Verify that the cron_run endpoint is fail-closed.
        """
        import backend.urls as urls
        from ops.monitoring import health_views as hv
        client = Client()

        # Case 1: CRON_API_KEY is not configured (empty string)
        original_key_urls = urls.CRON_API_KEY
        original_key_hv = hv.CRON_API_KEY
        try:
            urls.CRON_API_KEY = ""
            hv.CRON_API_KEY = ""
            
            # Request root urls.py cron view
            r = client.get('/api/cron/run/')
            assert r.status_code == 503
            assert r.json() == {'error': 'CRON_API_KEY not configured'}

            # Request health_views.py cron view directly
            from django.test import RequestFactory
            rf = RequestFactory()
            req = rf.get('/api/cron/run/')
            resp = hv.cron_run(req)
            assert resp.status_code == 503
            assert resp.content == b'{"error": "CRON_API_KEY not configured"}'

            # Case 2: CRON_API_KEY is configured
            urls.CRON_API_KEY = "supersecret_test_key"
            hv.CRON_API_KEY = "supersecret_test_key"

            # Request with no key
            r = client.get('/api/cron/run/')
            assert r.status_code == 403
            assert r.json() == {'error': 'Forbidden'}

            # Request with wrong key
            r = client.get('/api/cron/run/', HTTP_X_CRON_KEY='wrongkey')
            assert r.status_code == 403
            assert r.json() == {'error': 'Forbidden'}

            # Request with correct key (but missing parameters, which proves auth passed)
            r = client.get('/api/cron/run/', HTTP_X_CRON_KEY='supersecret_test_key')
            assert r.status_code == 400
            assert r.json() == {'error': 'Specify task= or group='}
        finally:
            urls.CRON_API_KEY = original_key_urls
            hv.CRON_API_KEY = original_key_hv

    def test_registration_response_does_not_expose_password(self):
        """
        Verify that registering a plan does not return temporary credentials/passwords.
        """
        client = Client()
        
        # Create a public active plan first
        plan = SubscriptionPlan.objects.create(
            name='basic',
            price=29.99,
            annual_price=299.99,
            is_active=True,
            is_public=True
        )

        registration_data = {
            'fullName': 'Test Owner',
            'email': 'security_test_owner@example.com',
            'businessName': 'Security Test Business',
            'phone': '1234567890',
            'address': '123 Security St',
            'planType': 'basic',
            'billingInterval': 'month'
        }

        # Send POST request to public register endpoint
        # The default auth settings require IsAuthenticated by default, but register_with_plan view has AllowAny
        r = client.post('/api/subscriptions/register/', registration_data, content_type='application/json')
        assert r.status_code == 201
        
        # Verify credentials block does not exist in response JSON
        resp_json = r.json()
        assert 'credentials' not in resp_json
        assert 'temporary_password' not in str(r.content)
        
        # Cleanup of other objects is handled by transaction rollback automatically

    def test_metrics_and_admin_conditional_on_debug(self):
        """
        Verify that admin/ and metrics/ are resolved ONLY when settings.DEBUG is True.
        """
        original_debug = settings.DEBUG
        try:
            # When DEBUG is True: admin and metrics must be resolved
            settings.DEBUG = True
            clear_url_caches()
            if 'backend.urls' in sys.modules:
                del sys.modules['backend.urls']
            
            assert resolve('/admin/').view_name == 'admin:index'
            assert resolve('/metrics').view_name == 'prometheus-django-metrics'

            # When DEBUG is False: admin and metrics must throw Resolver404
            settings.DEBUG = False
            clear_url_caches()
            if 'backend.urls' in sys.modules:
                del sys.modules['backend.urls']

            with pytest.raises(Resolver404):
                resolve('/admin/')

            with pytest.raises(Resolver404):
                resolve('/metrics')
        finally:
            settings.DEBUG = original_debug
            clear_url_caches()
            if 'backend.urls' in sys.modules:
                del sys.modules['backend.urls']

    def test_activate_subscription_is_completely_unresolved(self):
        """
        Verify that the dead method activate_subscription is not resolved under any circumstances.
        """
        with pytest.raises(Resolver404):
            resolve('/api/subscriptions/onboard/activate_subscription/')
