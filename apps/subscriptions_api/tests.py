import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.auth_api.models import User
from .models import SubscriptionPlan, UserSubscription
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


@pytest.mark.django_db
def test_create_subscription_plan_as_admin():
    admin = User.objects.create_superuser(email="admin@test.com", password="pass")
    client = APIClient()
    client.force_authenticate(admin)
    
    response = client.post(reverse("subscription-plan-list"), {
        "name": "basic",
        "description": "1 mes",
        "price": "19.99",
        "duration_month": 1
    })

    assert response.status_code == 201
    assert SubscriptionPlan.objects.count() == 1

@pytest.mark.django_db
def test_user_subscription_creation():
    user = User.objects.create_user(email="user@test.com", password="pass")
    plan = SubscriptionPlan.objects.create(name="basic", description="test", price=10, duration_month=1)
    
    client = APIClient()
    client.force_authenticate(user)
    
    response = client.post(reverse("user-subscription-list"), {
        "plan": plan.id,
        "end_date": (date.today() + timedelta(days=30)).isoformat()
    })

    assert response.status_code == 201
    assert UserSubscription.objects.filter(user=user).exists()


@pytest.fixture
def subscription_plans():
    return {
        'basic': SubscriptionPlan.objects.create(name='basic', price=10.00, duration_month=1),
        'standard': SubscriptionPlan.objects.create(name='standard', price=25.00, duration_month=3),
        'premium': SubscriptionPlan.objects.create(name='premium', price=80.00, duration_month=12),
    }

@pytest.fixture
def user(db):
    return User.objects.create_user(email='test@example.com', password='test1234')



@pytest.mark.django_db
def test_basic_subscription_duration(user, subscription_plans):
    plan = subscription_plans['basic']
    subscription = UserSubscription.objects.create(user=user, plan=plan)
    expected_end = subscription.start_date + relativedelta(months=1)
    assert subscription.end_date.date() == expected_end.date()

@pytest.mark.django_db
def test_standard_subscription_duration(user, subscription_plans):
    plan = subscription_plans['standard']
    subscription = UserSubscription.objects.create(user=user, plan=plan)
    expected_end = subscription.start_date + relativedelta(months=3)
    assert subscription.end_date.date() == expected_end.date()

@pytest.mark.django_db
def test_premium_subscription_duration(user, subscription_plans):
    plan = subscription_plans['premium']
    subscription = UserSubscription.objects.create(user=user, plan=plan)
    expected_end = subscription.start_date + relativedelta(months=12)
    assert subscription.end_date.date() == expected_end.date()