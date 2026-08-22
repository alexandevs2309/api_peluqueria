"""
Tests for plan catalog normalization and entitlement enforcement.

Covers:
- sync_plans idempotency
- Feature access per plan (all 4 tiers)
- Promotions gate (requires 'promotions' feature, not 'cash_register')
- Basic reports availability
- WhatsApp enforcement
- Export reports enforcement
- Branding enforcement
- Fallback matrix consistency
"""
import pytest
from decimal import Decimal
from django.test import TestCase
from apps.subscriptions_api.models import SubscriptionPlan
from apps.subscriptions_api.plan_consistency import (
    tenant_has_feature,
    get_feature_value,
    get_tenant_plan_features,
    FEATURE_ALIASES,
)
from apps.subscriptions_api.utils import get_user_feature_flag


# ---------------------------------------------------------------------------
# Sync Plans Idempotency
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSyncPlansIdempotency:
    """sync_plans must be safe to run multiple times."""

    def test_sync_plans_creates_all_plans(self):
        from django.core.management import call_command
        call_command('sync_plans', verbosity=0)

        plans = SubscriptionPlan.objects.filter(
            name__in=['basic', 'standard', 'premium', 'enterprise']
        )
        assert plans.count() == 4

    def test_sync_plans_is_idempotent(self):
        from django.core.management import call_command
        call_command('sync_plans', verbosity=0)
        count1 = SubscriptionPlan.objects.count()
        call_command('sync_plans', verbosity=0)
        count2 = SubscriptionPlan.objects.count()
        assert count1 == count2

    def test_sync_plans_updates_features(self):
        from django.core.management import call_command
        call_command('sync_plans', verbosity=0)

        basic = SubscriptionPlan.objects.get(name='basic')
        assert basic.features.get('cash_register') is True
        assert basic.features.get('reports') is True
        assert basic.features.get('promotions') is False

        standard = SubscriptionPlan.objects.get(name='standard')
        assert standard.features.get('promotions') is True
        assert standard.features.get('multi_location') is True

        premium = SubscriptionPlan.objects.get(name='premium')
        assert premium.features.get('whatsapp_notifications') is True
        assert premium.features.get('custom_branding') is True

        enterprise = SubscriptionPlan.objects.get(name='enterprise')
        assert enterprise.features.get('export_reports') is True
        assert enterprise.features.get('priority_support') is True

    def test_sync_plans_no_api_access(self):
        from django.core.management import call_command
        call_command('sync_plans', verbosity=0)

        for plan in SubscriptionPlan.objects.all():
            assert 'api_access' not in plan.features or plan.features.get('api_access') is False


# ---------------------------------------------------------------------------
# Feature Access Per Plan
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFeatureAccessPerPlan:
    """Verify each plan grants the correct features."""

    def test_basic_features(self):
        from apps.tenants_api.models import Tenant
        plan = SubscriptionPlan.objects.get(name='basic')
        tenant = Tenant.objects.create(
            name='Test Basic',
            subdomain='test-basic',
            subscription_plan=plan,
            plan_type='basic',
        )

        # Allowed
        assert tenant_has_feature(tenant, 'cash_register') is True
        assert tenant_has_feature(tenant, 'appointments') is True
        assert tenant_has_feature(tenant, 'inventory') is True
        assert tenant_has_feature(tenant, 'reports') is True
        assert tenant_has_feature(tenant, 'basic_reports') is True

        # Denied
        assert tenant_has_feature(tenant, 'promotions') is False
        assert tenant_has_feature(tenant, 'multi_location') is False
        assert tenant_has_feature(tenant, 'advanced_reports') is False
        assert tenant_has_feature(tenant, 'payroll') is False
        assert tenant_has_feature(tenant, 'custom_branding') is False
        assert tenant_has_feature(tenant, 'whatsapp_notifications') is False
        assert tenant_has_feature(tenant, 'export_reports') is False
        assert tenant_has_feature(tenant, 'priority_support') is False

    def test_standard_features(self):
        from apps.tenants_api.models import Tenant
        plan = SubscriptionPlan.objects.get(name='standard')
        tenant = Tenant.objects.create(
            name='Test Standard',
            subdomain='test-standard',
            subscription_plan=plan,
            plan_type='standard',
        )

        # Allowed
        assert tenant_has_feature(tenant, 'cash_register') is True
        assert tenant_has_feature(tenant, 'appointments') is True
        assert tenant_has_feature(tenant, 'inventory') is True
        assert tenant_has_feature(tenant, 'reports') is True
        assert tenant_has_feature(tenant, 'promotions') is True
        assert tenant_has_feature(tenant, 'multi_location') is True
        assert tenant_has_feature(tenant, 'advanced_reports') is True
        assert tenant_has_feature(tenant, 'payroll') is True

        # Denied
        assert tenant_has_feature(tenant, 'custom_branding') is False
        assert tenant_has_feature(tenant, 'whatsapp_notifications') is False
        assert tenant_has_feature(tenant, 'export_reports') is False
        assert tenant_has_feature(tenant, 'priority_support') is False

    def test_premium_features(self):
        from apps.tenants_api.models import Tenant
        plan = SubscriptionPlan.objects.get(name='premium')
        tenant = Tenant.objects.create(
            name='Test Premium',
            subdomain='test-premium',
            subscription_plan=plan,
            plan_type='premium',
        )

        # Allowed
        assert tenant_has_feature(tenant, 'cash_register') is True
        assert tenant_has_feature(tenant, 'appointments') is True
        assert tenant_has_feature(tenant, 'inventory') is True
        assert tenant_has_feature(tenant, 'reports') is True
        assert tenant_has_feature(tenant, 'promotions') is True
        assert tenant_has_feature(tenant, 'multi_location') is True
        assert tenant_has_feature(tenant, 'advanced_reports') is True
        assert tenant_has_feature(tenant, 'payroll') is True
        assert tenant_has_feature(tenant, 'custom_branding') is True
        assert tenant_has_feature(tenant, 'whatsapp_notifications') is True

        # Denied
        assert tenant_has_feature(tenant, 'export_reports') is False
        assert tenant_has_feature(tenant, 'priority_support') is False

    def test_enterprise_features(self):
        from apps.tenants_api.models import Tenant
        plan = SubscriptionPlan.objects.get(name='enterprise')
        tenant = Tenant.objects.create(
            name='Test Enterprise',
            subdomain='test-enterprise',
            subscription_plan=plan,
            plan_type='enterprise',
        )

        # All features allowed
        assert tenant_has_feature(tenant, 'cash_register') is True
        assert tenant_has_feature(tenant, 'appointments') is True
        assert tenant_has_feature(tenant, 'inventory') is True
        assert tenant_has_feature(tenant, 'reports') is True
        assert tenant_has_feature(tenant, 'promotions') is True
        assert tenant_has_feature(tenant, 'multi_location') is True
        assert tenant_has_feature(tenant, 'advanced_reports') is True
        assert tenant_has_feature(tenant, 'payroll') is True
        assert tenant_has_feature(tenant, 'custom_branding') is True
        assert tenant_has_feature(tenant, 'whatsapp_notifications') is True
        assert tenant_has_feature(tenant, 'export_reports') is True
        assert tenant_has_feature(tenant, 'priority_support') is True


# ---------------------------------------------------------------------------
# Promotions Gate
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPromotionsGate:
    """Promotions must require 'promotions' feature, not 'cash_register'."""

    def test_basic_plan_no_promotions(self):
        from apps.tenants_api.models import Tenant
        plan = SubscriptionPlan.objects.get(name='basic')
        tenant = Tenant.objects.create(
            name='Test Promotions Basic',
            subdomain='test-prom-basic',
            subscription_plan=plan,
            plan_type='basic',
        )
        assert tenant_has_feature(tenant, 'promotions') is False
        assert tenant_has_feature(tenant, 'cash_register') is True

    def test_standard_plan_has_promotions(self):
        from apps.tenants_api.models import Tenant
        plan = SubscriptionPlan.objects.get(name='standard')
        tenant = Tenant.objects.create(
            name='Test Promotions Standard',
            subdomain='test-prom-standard',
            subscription_plan=plan,
            plan_type='standard',
        )
        assert tenant_has_feature(tenant, 'promotions') is True


# ---------------------------------------------------------------------------
# Basic Reports
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBasicReports:
    """Basic plan must have basic reports."""

    def test_basic_has_reports(self):
        from apps.tenants_api.models import Tenant
        plan = SubscriptionPlan.objects.get(name='basic')
        tenant = Tenant.objects.create(
            name='Test Reports Basic',
            subdomain='test-reports-basic',
            subscription_plan=plan,
            plan_type='basic',
        )
        assert tenant_has_feature(tenant, 'reports') is True
        assert tenant_has_feature(tenant, 'basic_reports') is True


# ---------------------------------------------------------------------------
# Feature Aliases
# ---------------------------------------------------------------------------

class TestFeatureAliases:
    """Verify old feature names map to canonical names."""

    def test_pos_alias(self):
        assert get_feature_value({'cash_register': True}, 'pos') is True
        assert get_feature_value({'pos': True}, 'cash_register') is True

    def test_multi_branch_alias(self):
        assert get_feature_value({'multi_location': True}, 'multi_branch') is True
        assert get_feature_value({'multi_branch': True}, 'multi_location') is True

    def test_promotions_alias(self):
        assert get_feature_value({'promotions': True}, 'promotions_enabled') is True
        assert get_feature_value({'promotions_enabled': True}, 'promotions') is True

    def test_unknown_feature(self):
        assert get_feature_value({'pos': True}, 'nonexistent') is False
        assert get_feature_value({}, 'cash_register') is False


# ---------------------------------------------------------------------------
# Plan Limits
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPlanLimits:
    """Verify plan employee/user limits."""

    def test_basic_limits(self):
        plan = SubscriptionPlan.objects.get(name='basic')
        assert plan.max_employees == 3
        assert plan.max_users == 5
        assert plan.allows_multiple_branches is False

    def test_standard_limits(self):
        plan = SubscriptionPlan.objects.get(name='standard')
        assert plan.max_employees == 10
        assert plan.max_users == 15
        assert plan.allows_multiple_branches is True

    def test_premium_limits(self):
        plan = SubscriptionPlan.objects.get(name='premium')
        assert plan.max_employees == 25
        assert plan.max_users == 30
        assert plan.allows_multiple_branches is True

    def test_enterprise_limits(self):
        plan = SubscriptionPlan.objects.get(name='enterprise')
        assert plan.max_employees == 0  # unlimited
        assert plan.max_users == 0  # unlimited
        assert plan.allows_multiple_branches is True


# ---------------------------------------------------------------------------
# User Feature Flag (utils.py)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserFeatureFlag:
    """Test get_user_feature_flag with canonical feature names."""

    def test_superuser_has_all_features(self):
        from apps.auth_api.models import User
        user = User.objects.create_superuser(
            email='admin@test.com',
            password='testpass',
        )
        assert get_user_feature_flag(user, 'cash_register') is True
        assert get_user_feature_flag(user, 'promotions') is True
        assert get_user_feature_flag(user, 'export_reports') is True

    def test_basic_user_limited_features(self):
        from apps.auth_api.models import User
        from apps.tenants_api.models import Tenant
        plan = SubscriptionPlan.objects.get(name='basic')
        tenant = Tenant.objects.create(
            name='Test User Flag',
            subdomain='test-flag',
            subscription_plan=plan,
            plan_type='basic',
        )
        user = User.objects.create_user(
            email='user@test.com',
            password='testpass',
            tenant=tenant,
            role='Client-Admin',
        )
        # get_user_feature_flag uses subscription plan features
        assert get_user_feature_flag(user, 'cash_register') is True
        assert get_user_feature_flag(user, 'promotions') is False
