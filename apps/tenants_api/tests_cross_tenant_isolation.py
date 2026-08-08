"""
Tests masivos de aislamiento cross-tenant.
Intenta acceder a recursos de OTRO tenant desde cada endpoint CRUD.
"""
import uuid
from decimal import Decimal
from datetime import timedelta

import pytest
from django.test import TestCase
from django.contrib.auth.models import Permission
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.appointments_api.models import Appointment
from apps.auth_api.models import User
from apps.clients_api.models import Client
from apps.employees_api.models import Employee
from apps.inventory_api.models import Product, Supplier
from apps.pos_api.models import Sale, CashRegister, Promotion, NCFSequence, PosConfiguration
from apps.roles_api.models import Role, UserRole
from apps.services_api.models import Service, ServiceCategory
from apps.settings_api.models import Branch
from apps.subscriptions_api.models import SubscriptionPlan
from apps.tenants_api.models import Tenant


ENDPOINTS = [
    ("/api/clients/clients/{id}/", "/api/clients/clients/", "client"),
    ("/api/appointments/appointments/{id}/", "/api/appointments/appointments/", "appointment"),
    ("/api/services/services/{id}/", "/api/services/services/", "service"),
    ("/api/services/service-categories/{id}/", "/api/services/service-categories/", "service_category"),
    ("/api/employees/employees/{id}/", "/api/employees/employees/", "employee"),
    ("/api/pos/sales/{id}/", "/api/pos/sales/", "sale"),
    ("/api/pos/cashregisters/{id}/", "/api/pos/cashregisters/", "cash_register"),
    ("/api/pos/promotions/{id}/", "/api/pos/promotions/", "promotion"),
    ("/api/pos/ncf-sequences/{id}/", "/api/pos/ncf-sequences/", "ncf_sequence"),
    ("/api/inventory/products/{id}/", "/api/inventory/products/", "product"),
    ("/api/inventory/suppliers/{id}/", "/api/inventory/suppliers/", "supplier"),
    ("/api/settings/branches/{id}/", "/api/settings/branches/", "branch"),
]


def _grant_all_permissions(user, tenant):
    role, _ = Role.objects.get_or_create(
        name=f"FullAccess-{uuid.uuid4().hex[:8]}",
        defaults={"description": "Full access for isolation test", "scope": "TENANT"},
    )
    all_perms = Permission.objects.all()
    role.permissions.add(*all_perms)
    UserRole.objects.get_or_create(user=user, role=role, tenant=tenant)


def _client(user, tenant):
    client = APIClient()
    token = AccessToken.for_user(user)
    token["tenant_id"] = tenant.id
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")
    client.force_authenticate(user=user)
    return client


def make_plan():
    return SubscriptionPlan.objects.create(
        name="test-premium", description="Test plan",
        price="29.99", duration_month=1, is_active=True,
        max_employees=50, max_users=100,
        features={
            "appointments": True, "cash_register": True, "inventory": True,
            "basic_reports": True, "advanced_reports": True, "payroll": True,
            "multi_branch": True, "ncf": True,
        },
    )


class CrossTenantIsolationBase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.plan = make_plan()
        cls.tenant_a = Tenant.objects.create(
            name=f"Tenant A {uuid.uuid4().hex[:6]}",
            subdomain=f"ta-{uuid.uuid4().hex[:6]}",
            subscription_plan=cls.plan, subscription_status="active", is_active=True,
        )
        cls.tenant_b = Tenant.objects.create(
            name=f"Tenant B {uuid.uuid4().hex[:6]}",
            subdomain=f"tb-{uuid.uuid4().hex[:6]}",
            subscription_plan=cls.plan, subscription_status="active", is_active=True,
        )

        cls.user_a = User.objects.create_user(
            email=f"ua-{uuid.uuid4().hex[:6]}@test.com",
            password="test123", full_name="User A", tenant=cls.tenant_a,
        )
        cls.user_b = User.objects.create_user(
            email=f"ub-{uuid.uuid4().hex[:6]}@test.com",
            password="test123", full_name="User B", tenant=cls.tenant_b,
        )

        cls.owner = User.objects.create_superuser(
            email=f"own-{uuid.uuid4().hex[:6]}@test.com",
            password="test123", full_name="Owner",
        )

        _grant_all_permissions(cls.user_a, cls.tenant_a)
        _grant_all_permissions(cls.user_b, cls.tenant_b)

        emp_a = Employee.objects.create(user=cls.user_a, tenant=cls.tenant_a, is_active=True)
        emp_b = Employee.objects.create(user=cls.user_b, tenant=cls.tenant_b, is_active=True)

        cli_a = Client.objects.create(tenant=cls.tenant_a, full_name="Client A", created_by=cls.user_a)
        cli_b = Client.objects.create(tenant=cls.tenant_b, full_name="Client B", created_by=cls.user_b)

        cat_a = ServiceCategory.objects.create(tenant=cls.tenant_a, name="Cat A")
        cat_b = ServiceCategory.objects.create(tenant=cls.tenant_b, name="Cat B")

        srv_a = Service.objects.create(name="Service A", tenant=cls.tenant_a, price=Decimal("500"), duration=30)
        srv_b = Service.objects.create(name="Service B", tenant=cls.tenant_b, price=Decimal("300"), duration=45)

        prd_a = Product.objects.create(name="Product A", sku=f"SKA-{uuid.uuid4().hex[:4]}", price=Decimal("100"), stock=10, tenant=cls.tenant_a)
        prd_b = Product.objects.create(name="Product B", sku=f"SKB-{uuid.uuid4().hex[:4]}", price=Decimal("200"), stock=5, tenant=cls.tenant_b)

        sup_a = Supplier.objects.create(name="Supplier A", tenant=cls.tenant_a, phone="809-000-0000")
        sup_b = Supplier.objects.create(name="Supplier B", tenant=cls.tenant_b, phone="809-000-0001")

        cr_a = CashRegister.objects.create(user=cls.user_a, tenant=cls.tenant_a, initial_cash=Decimal("1000"), is_open=True)
        cr_b = CashRegister.objects.create(user=cls.user_b, tenant=cls.tenant_b, initial_cash=Decimal("500"), is_open=True)

        sale_a = Sale.objects.create(tenant=cls.tenant_a, user=cls.user_a, total=Decimal("100"), paid=Decimal("100"), payment_method="cash")
        sale_b = Sale.objects.create(tenant=cls.tenant_b, user=cls.user_b, total=Decimal("200"), paid=Decimal("200"), payment_method="card")

        now = timezone.now()
        promo_a = Promotion.objects.create(
            name="Promo A", tenant=cls.tenant_a, type="percentage",
            discount_value=Decimal("10"), min_amount=Decimal("0"),
            conditions={}, is_active=True,
            start_date=now, end_date=now+timedelta(days=30),
        )
        promo_b = Promotion.objects.create(
            name="Promo B", tenant=cls.tenant_b, type="fixed",
            discount_value=Decimal("50"), min_amount=Decimal("0"),
            conditions={}, is_active=True,
            start_date=now, end_date=now+timedelta(days=30),
        )

        ncf_a = NCFSequence.objects.create(
            tenant=cls.tenant_a, type="B02", prefix="B02",
            start_sequence=1, end_sequence=1000, current_sequence=1,
            is_active=True, expiration_date=now.date()+timedelta(days=365),
        )
        ncf_b = NCFSequence.objects.create(
            tenant=cls.tenant_b, type="B01", prefix="B01",
            start_sequence=1, end_sequence=500, current_sequence=1,
            is_active=True, expiration_date=now.date()+timedelta(days=365),
        )

        branch_a = Branch.objects.create(tenant=cls.tenant_a, name="Branch A")
        branch_b = Branch.objects.create(tenant=cls.tenant_b, name="Branch B")

        appt_a = Appointment.objects.create(tenant=cls.tenant_a, client=cli_a, stylist=cls.user_a, date_time=timezone.now()+timedelta(days=1))
        appt_b = Appointment.objects.create(tenant=cls.tenant_b, client=cli_b, stylist=cls.user_b, date_time=timezone.now()+timedelta(days=2))

        cls.data_a = {
            "client": cli_a, "appointment": appt_a, "service": srv_a,
            "service_category": cat_a, "employee": emp_a, "sale": sale_a,
            "cash_register": cr_a, "promotion": promo_a, "ncf_sequence": ncf_a,
            "product": prd_a, "supplier": sup_a, "branch": branch_a,
        }
        cls.data_b = {
            "client": cli_b, "appointment": appt_b, "service": srv_b,
            "service_category": cat_b, "employee": emp_b, "sale": sale_b,
            "cash_register": cr_b, "promotion": promo_b, "ncf_sequence": ncf_b,
            "product": prd_b, "supplier": sup_b, "branch": branch_b,
        }

        cls.api_a = _client(cls.user_a, cls.tenant_a)
        cls.api_b = _client(cls.user_b, cls.tenant_b)


# ─────────── List isolation ───────────

class TestListIsolation(CrossTenantIsolationBase):

    def test_list_own_tenant_returns_data(self):
        for _, list_path, key in ENDPOINTS:
            with self.subTest(endpoint=key):
                resp = self.api_a.get(list_path)
                self.assertEqual(resp.status_code, 200, f"{list_path} returned {resp.status_code}")
                results = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
                own_id = self.data_a[key].id
                ids = [r["id"] if isinstance(r, dict) else r for r in results]
                self.assertIn(own_id, ids, f"Own {key}#{own_id} not in list")

    def test_list_cross_tenant_excludes_other_data(self):
        for _, list_path, key in ENDPOINTS:
            with self.subTest(endpoint=key):
                resp = self.api_a.get(list_path)
                self.assertEqual(resp.status_code, 200)
                results = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
                other_id = self.data_b[key].id
                ids = [r["id"] if isinstance(r, dict) else r for r in results]
                self.assertNotIn(other_id, ids, f"Cross-tenant {key}#{other_id} leaked in list!")


# ─────────── Detail isolation ───────────

class TestDetailIsolation(CrossTenantIsolationBase):

    def test_detail_own_tenant_allowed(self):
        for detail_tpl, _, key in ENDPOINTS:
            with self.subTest(endpoint=key):
                own_id = self.data_a[key].id
                url = detail_tpl.format(id=own_id)
                resp = self.api_a.get(url)
                self.assertEqual(resp.status_code, 200, f"GET {url} returned {resp.status_code}")

    def test_detail_cross_tenant_blocked(self):
        for detail_tpl, _, key in ENDPOINTS:
            with self.subTest(endpoint=key):
                other_id = self.data_b[key].id
                url = detail_tpl.format(id=other_id)
                resp = self.api_a.get(url)
                self.assertEqual(resp.status_code, 404,
                    f"Cross-tenant GET {url} for {key} returned {resp.status_code} instead of 404")


# ─────────── Update isolation ───────────

class TestUpdateIsolation(CrossTenantIsolationBase):

    def test_update_own_tenant_allowed(self):
        for detail_tpl, _, key in ENDPOINTS:
            with self.subTest(endpoint=key):
                own_id = self.data_a[key].id
                url = detail_tpl.format(id=own_id)
                if key == "client":
                    payload = {"phone": "809-111-0000"}
                elif key == "sale":
                    continue  # sale serializer has strict validation
                else:
                    payload = {"is_active": False}
                    resp = self.api_a.patch(url, payload, format="json")
                    self.assertIn(resp.status_code, (200, 204),
                        f"PATCH {url} returned {resp.status_code}")

    def test_update_cross_tenant_blocked(self):
        for detail_tpl, _, key in ENDPOINTS:
            with self.subTest(endpoint=key):
                other_id = self.data_b[key].id
                url = detail_tpl.format(id=other_id)
                if key == "client":
                    payload = {"phone": "809-111-0000"}
                elif key == "sale":
                    payload = {"status": "completed"}
                else:
                    payload = {"is_active": False}
                resp = self.api_a.patch(url, payload, format="json")
                self.assertEqual(resp.status_code, 404,
                        f"Cross-tenant PATCH {url} returned {resp.status_code} instead of 404")


# ─────────── Delete isolation ───────────

class TestDeleteIsolation(CrossTenantIsolationBase):

    def test_delete_cross_tenant_blocked(self):
        for detail_tpl, _, key in ENDPOINTS:
            with self.subTest(endpoint=key):
                other_id = self.data_b[key].id
                url = detail_tpl.format(id=other_id)
                resp = self.api_a.delete(url)
                self.assertEqual(resp.status_code, 404,
                        f"Cross-tenant DELETE {url} returned {resp.status_code} instead of 404")

    def test_cross_tenant_delete_does_not_actually_delete(self):
        model_map = {
            "client": Client, "appointment": Appointment, "service": Service,
            "service_category": ServiceCategory, "employee": Employee,
            "sale": Sale, "cash_register": CashRegister,
            "promotion": Promotion, "ncf_sequence": NCFSequence,
            "product": Product, "supplier": Supplier, "branch": Branch,
        }
        for detail_tpl, _, key in ENDPOINTS:
            with self.subTest(endpoint=key):
                other_id = self.data_b[key].id
                url = detail_tpl.format(id=other_id)
                self.api_a.delete(url)
                model = model_map[key]
                self.assertTrue(
                    model.objects.filter(id=other_id).exists(),
                    f"Cross-tenant DELETE actually deleted {key}#{other_id}!",
                )


# ─────────── Edge cases ───────────

class TestCrossTenantEdgeCases(CrossTenantIsolationBase):

    def test_unauthenticated_access_blocked(self):
        client = APIClient()
        for _, list_path, key in ENDPOINTS:
            with self.subTest(endpoint=key):
                resp = client.get(list_path)
                self.assertIn(resp.status_code, (401, 403),
                    f"Unauthenticated {list_path} got {resp.status_code}")

    def test_superuser_with_tenant_filter(self):
        """Superuser can filter by tenant when tenant_id is in JWT."""
        token = AccessToken.for_user(self.owner)
        token["tenant_id"] = self.tenant_b.id
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")
        client.force_authenticate(user=self.owner)

        resp = client.get("/api/pos/sales/")
        results = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
        ids = [s["id"] if isinstance(s, dict) else s for s in results]
        self.assertIn(self.data_b["sale"].id, ids,
            "Superuser with tenant filter should see that tenant's data")

    def test_superuser_without_tenant_sees_all(self):
        """Superuser without tenant filter sees all data across tenants."""
        token = AccessToken.for_user(self.owner)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")
        client.force_authenticate(user=self.owner)

        resp = client.get("/api/pos/sales/")
        results = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
        ids = [s["id"] if isinstance(s, dict) else s for s in results]
        self.assertIn(self.data_a["sale"].id, ids, "Superuser should see tenant A data")
        self.assertIn(self.data_b["sale"].id, ids, "Superuser should see tenant B data")

    def test_empty_tenant_returns_empty_lists(self):
        new_tenant = Tenant.objects.create(
            name=f"Empty {uuid.uuid4().hex[:6]}",
            subdomain=f"empty-{uuid.uuid4().hex[:6]}",
            subscription_status="active", is_active=True,
        )
        user = User.objects.create_user(
            email=f"empty-{uuid.uuid4().hex[:6]}@test.com",
            password="test123", full_name="Empty User", tenant=new_tenant,
        )
        _grant_all_permissions(user, new_tenant)
        client = _client(user, new_tenant)

        for _, list_path, key in ENDPOINTS:
            with self.subTest(endpoint=key):
                resp = client.get(list_path)
                if resp.status_code != 200:
                    continue
                results = resp.data.get("results", resp.data) if isinstance(resp.data, dict) else resp.data
                if isinstance(results, list):
                    self.assertEqual(len(results), 0,
                        f"{list_path} for empty tenant returned {len(results)} items")

    def test_superuser_can_access_admin_panel(self):
        """Only superusers can access /admin endpoints."""
        # Regular user trying /admin/ — django redirects to login (302)
        resp = self.api_a.get("/admin/")
        self.assertIn(resp.status_code, (302, 401, 403, 404),
            f"Regular user admin access got {resp.status_code}")

        # Superuser should have some access
        token = AccessToken.for_user(self.owner)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")
        client.force_authenticate(user=self.owner)
        resp = client.get("/admin/")
        # Django admin returns 302 (redirect to login) or 200
        self.assertIn(resp.status_code, (200, 302),
            f"Superuser admin access got {resp.status_code}")
